from pathlib import Path
from unittest.mock import Mock

from app.config import load_scoring_config
from app.models import Criterion, CriterionScore, CriterionScoringResult
from app.services import scorer


SAMPLES_DIR = Path(__file__).resolve().parents[1] / "samples"
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
def _criterion_scores(scores: list[int]) -> CriterionScoringResult:
    return CriterionScoringResult(
        scores=[
            CriterionScore(
                criterion_id=criterion.id,
                score=score,
                evidence=[f"Mocked evidence for {criterion.id}"],
                reasoning="Deterministic calibration evidence.",
            )
            for criterion, score in zip(CALIBRATION_CRITERIA, scores)
        ]
    )


def _calibrated_sample_scores(mock_scores: list[list[int]]) -> list[float]:
    mocked_scorer = Mock()
    mocked_scorer.side_effect = [
        _criterion_scores(scores) for scores in mock_scores
    ]

    original_scorer = scorer.score_resume_against_criteria
    scorer.score_resume_against_criteria = mocked_scorer
    try:
        results = []
        for sample_path in SAMPLE_RESUMES:
            resume_text = sample_path.read_text(encoding="utf-8")
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
    scores = _calibrated_sample_scores(
        [
            [4, 4, 3],  # resume_1: strong fit
            [3, 2, 2],  # resume_2: moderate fit
            [1, 1, 0],  # resume_3: weaker fit
        ]
    )

    assert all(0 <= score <= 100 for score in scores)
    assert scores[0] > scores[1] > scores[2]
    assert len(set(scores)) == 3
    assert scores[0] - scores[1] < 40


def test_sample_resume_calibration_is_deterministic() -> None:
    scenarios = [[4, 4, 3], [3, 2, 2], [1, 1, 0]]

    first_run = _calibrated_sample_scores(scenarios)
    second_run = _calibrated_sample_scores(scenarios)

    assert first_run == second_run
    assert first_run == [95.0, 60.0, 20.0]


def test_calibration_uses_each_sample_resume() -> None:
    assert [sample.name for sample in SAMPLE_RESUMES] == [
        "resume_1.txt",
        "resume_2.txt",
        "resume_3.txt",
    ]
    assert all(sample.exists() for sample in SAMPLE_RESUMES)
