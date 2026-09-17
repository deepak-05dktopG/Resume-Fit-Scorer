from pathlib import Path

from app.config import load_scoring_config
from app.models import Criterion, CriterionScore, CriterionScoringResult
from app.services import scorer


SAMPLES_DIR = Path(__file__).resolve().parents[1] / "samples"
JOB_DESCRIPTION_PATH = SAMPLES_DIR / "jd.txt"
SAMPLE_RESUMES = [
    SAMPLES_DIR / "resume_1.txt",
    SAMPLES_DIR / "resume_2.txt",
    SAMPLES_DIR / "resume_3.txt",
]

CALIBRATION_CRITERIA = [
    Criterion(
        id="python",
        name="Python",
        description="Experience developing software with Python",
        importance="required",
    ),
    Criterion(
        id="rest_api",
        name="REST APIs",
        description="Experience developing REST APIs",
        importance="required",
    ),
    Criterion(
        id="communication",
        name="Communication",
        description="Clear written and verbal communication",
        importance="preferred",
    ),
]


# These are calibration checks for score consistency, not claims about hiring accuracy.
def _criterion_scores(resume_text: str) -> CriterionScoringResult:
    """Create deterministic mock scores from evidence present in one sample resume."""

    text = resume_text.lower()
    scores = {
        "python": _score_python_evidence(text),
        "rest_api": _score_api_evidence(text),
        "communication": _score_communication_evidence(text),
    }

    return CriterionScoringResult(
        scores=[
            CriterionScore(
                criterion_id=criterion.id,
                score=scores[criterion.id],
                evidence=[f"Evidence found in sample resume for {criterion.id}"],
                reasoning="Deterministic calibration mock based on resume text.",
            )
            for criterion in CALIBRATION_CRITERIA
        ]
    )


def _score_python_evidence(text: str) -> int:
    if "python services" in text and "fastapi" in text:
        return 4
    if "python features" in text or "python applications" in text:
        return 3
    if "basic python" in text or "python scripts" in text:
        return 1
    return 0


def _score_api_evidence(text: str) -> int:
    if "versioned rest apis" in text and "fastapi service" in text:
        return 4
    if "rest endpoints" in text and "flask api" in text:
        return 3
    return 0


def _score_communication_evidence(text: str) -> int:
    if "communicating technical decisions" in text or "presented delivery plans" in text:
        return 3
    if "communicated fixes" in text or "worked with designers" in text:
        return 2
    if "explained technical issues" in text or "technical documentation" in text:
        return 2
    return 0


def _calibrated_sample_scores() -> list[float]:
    """Read each sample and route its text through the mocked scoring boundary."""

    original_scorer = scorer.score_resume_against_criteria
    scorer.score_resume_against_criteria = lambda resume_text, criteria: _criterion_scores(
        resume_text
    )
    try:
        results = []
        for sample_path in SAMPLE_RESUMES:
            resume_text = sample_path.read_text(encoding="utf-8")
            assert resume_text.strip()
            criterion_result = scorer.score_resume_against_criteria(
                resume_text,
                CALIBRATION_CRITERIA,
            )
            assessment = scorer.calculate_overall_score(
                criterion_result.scores,
                CALIBRATION_CRITERIA,
                load_scoring_config().weights,
            )
            results.append(assessment.overall_score)
        return results
    finally:
        scorer.score_resume_against_criteria = original_scorer


def test_sample_resume_calibration_scores_are_meaningfully_ordered() -> None:
    scores = _calibrated_sample_scores()

    assert all(0 <= score <= 100 for score in scores)
    assert scores[0] > scores[1] > scores[2]
    assert len(set(scores)) == 3
    # The strong and moderate samples are the reasonably similar pair.
    assert scores[0] - scores[1] < 40


def test_sample_resume_calibration_is_deterministic() -> None:
    first_run = _calibrated_sample_scores()
    second_run = _calibrated_sample_scores()

    assert first_run == second_run


def test_calibration_uses_each_sample_resume() -> None:
    assert JOB_DESCRIPTION_PATH.exists()
    assert [sample.name for sample in SAMPLE_RESUMES] == [
        "resume_1.txt",
        "resume_2.txt",
        "resume_3.txt",
    ]
    assert all(sample.exists() for sample in SAMPLE_RESUMES)
