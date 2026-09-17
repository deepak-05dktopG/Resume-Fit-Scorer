from unittest.mock import Mock

import pytest

from app.models import CriterionImportance
from app.services import criteria_extractor
from app.services.criteria_extractor import CriteriaExtractionError, extract_criteria


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
