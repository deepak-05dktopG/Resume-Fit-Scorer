from unittest.mock import Mock

import pytest

from app.config import ScoringWeights, load_scoring_config
from app.models import Criterion, CriterionImportance, CriterionScore
from app.services import criteria_extractor
from app.services.criteria_extractor import CriteriaExtractionError, extract_criteria
from app.services import scorer
from app.services.scorer import (
	ScoringError,
	calculate_overall_score,
	score_resume_against_criteria,
)


JOB_DESCRIPTION = "We need a Python engineer with FastAPI experience. Communication skills are preferred."


def test_extract_criteria_valid_response(monkeypatch: pytest.MonkeyPatch) -> None:
	client = Mock()
	client.complete.return_value = '{"criteria": [{"id": "python", "name": "Python", "description": "Python development", "importance": "required"}, {"id": "fastapi", "name": "FastAPI", "description": "FastAPI experience", "importance": "preferred"}]}'
	monkeypatch.setattr(criteria_extractor, "llm_client", client)

	result = extract_criteria(JOB_DESCRIPTION)

	assert len(result.criteria) == 2
	assert result.criteria[0].id == "python"
	assert result.criteria[0].importance is CriterionImportance.required
	assert result.criteria[1].importance is CriterionImportance.preferred


def test_prompt_requires_explicit_deduplicated_nonweighted_json(monkeypatch: pytest.MonkeyPatch) -> None:
	client = Mock()
	client.complete.return_value = '{"criteria": []}'
	monkeypatch.setattr(criteria_extractor, "llm_client", client)

	extract_criteria(JOB_DESCRIPTION)
	system_prompt, user_prompt = client.complete.call_args.args

	assert "only hiring criteria explicitly supported" in system_prompt
	assert "combine duplicate requirements" in system_prompt
	assert "Do not assign numeric weights" in system_prompt
	assert "markdown fences" in system_prompt
	assert JOB_DESCRIPTION in user_prompt


def test_extract_criteria_rejects_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
	client = Mock()
	client.complete.return_value = "not valid json"
	monkeypatch.setattr(criteria_extractor, "llm_client", client)

	with pytest.raises(CriteriaExtractionError, match="invalid structured"):
		extract_criteria(JOB_DESCRIPTION)


@pytest.mark.parametrize(
	"response",
	[
		'{"criteria": [{"id": "python", "name": "Python", "description": "Python", "importance": "maybe"}]}',
		'{"criteria": [{"id": "python", "name": "Python"}]}',
	],
)
def test_extract_criteria_rejects_invalid_schema(
	monkeypatch: pytest.MonkeyPatch, response: str
) -> None:
	client = Mock()
	client.complete.return_value = response
	monkeypatch.setattr(criteria_extractor, "llm_client", client)

	with pytest.raises(CriteriaExtractionError, match="invalid structured"):
		extract_criteria(JOB_DESCRIPTION)


def test_empty_job_description_is_rejected_before_llm_call(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	client = Mock()
	monkeypatch.setattr(criteria_extractor, "llm_client", client)

	with pytest.raises(CriteriaExtractionError, match="cannot be empty"):
		extract_criteria("  \n")

	client.complete.assert_not_called()


RESUME_TEXT = "Built backend services in Python and FastAPI for a production API."
PYTHON_CRITERION = Criterion(
	id="python",
	name="Python",
	description="Experience developing software using Python",
	importance="required",
)
FASTAPI_CRITERION = Criterion(
	id="fastapi",
	name="FastAPI",
	description="Experience building APIs with FastAPI",
	importance="preferred",
)


def test_score_single_criterion(monkeypatch: pytest.MonkeyPatch) -> None:
	client = Mock()
	client.complete.return_value = '{"criterion_id": "python", "score": 3, "evidence": ["Built backend services in Python"], "reasoning": "The resume clearly demonstrates Python development experience."}'
	monkeypatch.setattr(scorer, "llm_client", client)

	result = score_resume_against_criteria(RESUME_TEXT, [PYTHON_CRITERION])

	assert len(result.scores) == 1
	assert result.scores[0].criterion_id == "python"
	assert result.scores[0].score == 3
	assert result.scores[0].evidence == ["Built backend services in Python"]
	assert result.scores[0].reasoning.startswith("The resume clearly")


def test_score_multiple_criteria_independently(monkeypatch: pytest.MonkeyPatch) -> None:
	client = Mock()
	client.complete.side_effect = [
		'{"criterion_id": "python", "score": 3, "evidence": ["Built backend services in Python"], "reasoning": "Strong evidence."}',
		'{"criterion_id": "fastapi", "score": 4, "evidence": ["Built a production API with FastAPI"], "reasoning": "Direct evidence."}',
	]
	monkeypatch.setattr(scorer, "llm_client", client)

	result = score_resume_against_criteria(
		RESUME_TEXT,
		[PYTHON_CRITERION, FASTAPI_CRITERION],
	)

	assert [item.criterion_id for item in result.scores] == ["python", "fastapi"]
	assert client.complete.call_count == 2


@pytest.mark.parametrize("invalid_score", [-1, 5])
def test_score_rejects_out_of_range_scores(
	monkeypatch: pytest.MonkeyPatch, invalid_score: int
) -> None:
	client = Mock()
	client.complete.return_value = f'{{"criterion_id": "python", "score": {invalid_score}, "evidence": [], "reasoning": "Invalid score."}}'
	monkeypatch.setattr(scorer, "llm_client", client)

	with pytest.raises(ScoringError, match="invalid structured"):
		score_resume_against_criteria(RESUME_TEXT, [PYTHON_CRITERION])


def test_score_rejects_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
	client = Mock()
	client.complete.return_value = "not valid json"
	monkeypatch.setattr(scorer, "llm_client", client)

	with pytest.raises(ScoringError, match="invalid structured"):
		score_resume_against_criteria(RESUME_TEXT, [PYTHON_CRITERION])


@pytest.mark.parametrize(
	"response",
	[
		'{"criterion_id": "python", "score": 3, "reasoning": "Missing evidence."}',
		'{"criterion_id": "python", "score": 3, "evidence": ["Python"], "reasoning": ""}',
	],
)
def test_score_rejects_missing_or_invalid_required_fields(
	monkeypatch: pytest.MonkeyPatch, response: str
) -> None:
	client = Mock()
	client.complete.return_value = response
	monkeypatch.setattr(scorer, "llm_client", client)

	with pytest.raises(ScoringError, match="invalid structured"):
		score_resume_against_criteria(RESUME_TEXT, [PYTHON_CRITERION])


def test_score_rejects_wrong_criterion_id(monkeypatch: pytest.MonkeyPatch) -> None:
	client = Mock()
	client.complete.return_value = '{"criterion_id": "fastapi", "score": 3, "evidence": ["FastAPI"], "reasoning": "Wrong criterion."}'
	monkeypatch.setattr(scorer, "llm_client", client)

	with pytest.raises(ScoringError, match="wrong criterion"):
		score_resume_against_criteria(RESUME_TEXT, [PYTHON_CRITERION])


def test_empty_resume_is_rejected_before_llm_call(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	client = Mock()
	monkeypatch.setattr(scorer, "llm_client", client)

	with pytest.raises(ScoringError, match="Resume text cannot be empty"):
		score_resume_against_criteria("  \n", [PYTHON_CRITERION])

	client.complete.assert_not_called()


def test_empty_criteria_are_rejected_before_llm_call(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	client = Mock()
	monkeypatch.setattr(scorer, "llm_client", client)

	with pytest.raises(ScoringError, match="Criteria cannot be empty"):
		score_resume_against_criteria(RESUME_TEXT, [])

	client.complete.assert_not_called()


def test_scoring_prompt_contains_criterion_resume_rubric_and_constraints(
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	client = Mock()
	client.complete.return_value = '{"criterion_id": "python", "score": 2, "evidence": ["Python"], "reasoning": "Partial evidence."}'
	monkeypatch.setattr(scorer, "llm_client", client)

	score_resume_against_criteria(RESUME_TEXT, [PYTHON_CRITERION])
	system_prompt, user_prompt = client.complete.call_args.args

	assert "resume evaluation assistant" in system_prompt
	assert PYTHON_CRITERION.id in user_prompt
	assert PYTHON_CRITERION.name in user_prompt
	assert PYTHON_CRITERION.description in user_prompt
	assert RESUME_TEXT in user_prompt
	assert "0 = No evidence" in user_prompt
	assert "4 = Direct / highly relevant evidence" in user_prompt
	assert "Do not infer unsupported skills" in system_prompt
	assert "Return ONLY JSON" in user_prompt


def _criterion_score(criterion_id: str, score: int) -> CriterionScore:
	return CriterionScore(
		criterion_id=criterion_id,
		score=score,
		evidence=["Resume evidence"],
		reasoning="Validated reasoning.",
	)


def test_overall_score_is_100_when_all_criteria_score_4() -> None:
	result = calculate_overall_score(
		[_criterion_score("python", 4), _criterion_score("fastapi", 4)],
		[PYTHON_CRITERION, FASTAPI_CRITERION],
	)

	assert result.overall_score == 100.0


def test_overall_score_is_0_when_all_criteria_score_0() -> None:
	result = calculate_overall_score(
		[_criterion_score("python", 0), _criterion_score("fastapi", 0)],
		[PYTHON_CRITERION, FASTAPI_CRITERION],
	)

	assert result.overall_score == 0.0


def test_overall_score_uses_required_and_preferred_weights() -> None:
	criteria = [
		PYTHON_CRITERION,
		Criterion(
			id="rest_api",
			name="REST APIs",
			description="Experience developing REST APIs",
			importance="required",
		),
		Criterion(
			id="communication",
			name="Communication",
			description="Clear communication",
			importance="preferred",
		),
	]
	result = calculate_overall_score(
		[
			_criterion_score("python", 4),
			_criterion_score("rest_api", 2),
			_criterion_score("communication", 4),
		],
		criteria,
		ScoringWeights(required=2.0, preferred=1.0),
	)

	assert result.overall_score == 80.0


def test_changing_configured_weight_changes_result() -> None:
	criteria = [PYTHON_CRITERION, FASTAPI_CRITERION]
	scores = [_criterion_score("python", 4), _criterion_score("fastapi", 0)]

	default_result = calculate_overall_score(scores, criteria, load_scoring_config().weights)
	changed_result = calculate_overall_score(
		scores,
		criteria,
		ScoringWeights(required=3.0, preferred=1.0),
	)

	assert default_result.overall_score == 66.67
	assert changed_result.overall_score == 75.0


def test_overall_score_rejects_missing_criterion_score() -> None:
	with pytest.raises(ScoringError, match="missing"):
		calculate_overall_score([_criterion_score("python", 4)], [PYTHON_CRITERION, FASTAPI_CRITERION])


def test_overall_score_rejects_unknown_criterion_id() -> None:
	with pytest.raises(ScoringError, match="unknown"):
		calculate_overall_score(
			[_criterion_score("unknown", 4)],
			[PYTHON_CRITERION],
		)


def test_overall_score_rejects_duplicate_criterion_score() -> None:
	with pytest.raises(ScoringError, match="duplicate"):
		calculate_overall_score(
			[_criterion_score("python", 4), _criterion_score("python", 3)],
			[PYTHON_CRITERION],
		)


def test_overall_score_rejects_zero_total_weight() -> None:
	with pytest.raises(ScoringError, match="greater than zero"):
		calculate_overall_score(
			[_criterion_score("python", 4)],
			[PYTHON_CRITERION],
			ScoringWeights(required=0.0, preferred=0.0),
		)


def test_criterion_score_rejects_score_outside_range() -> None:
	with pytest.raises(ValueError):
		_criterion_score("python", 5)


def test_overall_score_rounds_to_two_decimal_places() -> None:
	result = calculate_overall_score(
		[_criterion_score("python", 1), _criterion_score("fastapi", 2)],
		[PYTHON_CRITERION, FASTAPI_CRITERION],
	)

	assert result.overall_score == 33.33
