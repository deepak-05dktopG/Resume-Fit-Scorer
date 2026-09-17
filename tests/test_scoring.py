from unittest.mock import Mock

import pytest

from app.models import Criterion, CriterionImportance
from app.services import criteria_extractor
from app.services.criteria_extractor import CriteriaExtractionError, extract_criteria
from app.services import scorer
from app.services.scorer import ScoringError, score_resume_against_criteria


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
