from io import BytesIO
from unittest.mock import Mock

import fitz
from fastapi.testclient import TestClient

from app.main import app
from app.services import criteria_extractor, scorer
from app.models import Criterion, CriterionScore, CriterionScoringResult


client = TestClient(app)


def test_health_check() -> None:
	response = client.get("/health")

	assert response.status_code == 200
	assert response.json() == {
		"status": "ok",
		"service": "resume-fit-scorer",
	}


def _mock_pipeline(monkeypatch) -> None:
	criteria = [
		Criterion(
			id="python",
			name="Python",
			description="Python development",
			importance="required",
		)
	]
	monkeypatch.setattr(criteria_extractor, "extract_criteria", lambda job_description: type("Extraction", (), {"criteria": criteria})())
	monkeypatch.setattr(
		scorer,
		"score_resume_against_criteria",
		lambda resume_text, extracted_criteria: CriterionScoringResult(
			scores=[
				CriterionScore(
					criterion_id="python",
					score=4,
					evidence=["Built Python services"],
					reasoning="Direct evidence.",
				)
			]
		),
	)


def test_answer_with_txt_resume(monkeypatch) -> None:
	_mock_pipeline(monkeypatch)

	response = client.post(
		"/answer",
		data={"job_description": "Need Python experience."},
		files={"resume": ("resume.txt", b"Built Python services.", "text/plain")},
	)

	assert response.status_code == 200
	assert response.json() == {
		"overall_score": 100.0,
		"criteria": [
			{
				"id": "python",
				"name": "Python",
				"importance": "required",
				"score": 4,
				"evidence": ["Built Python services"],
				"reasoning": "Direct evidence.",
			}
		],
	}


def test_answer_with_pdf_resume(monkeypatch) -> None:
	_mock_pipeline(monkeypatch)
	document = fitz.open()
	page = document.new_page()
	page.insert_text((72, 72), "Python engineer with extensive production service experience.")
	pdf_bytes = document.tobytes()
	document.close()

	response = client.post(
		"/answer",
		data={"job_description": "Need Python experience."},
		files={"resume": ("resume.pdf", BytesIO(pdf_bytes), "application/pdf")},
	)

	assert response.status_code == 200
	assert response.json()["overall_score"] == 100.0


def test_answer_rejects_missing_job_description() -> None:
	response = client.post(
		"/answer",
		files={"resume": ("resume.txt", b"Python experience", "text/plain")},
	)

	assert response.status_code == 422


def test_answer_rejects_missing_resume() -> None:
	response = client.post(
		"/answer",
		data={"job_description": "Need Python experience."},
	)

	assert response.status_code == 422


def test_answer_rejects_unsupported_resume_type() -> None:
	response = client.post(
		"/answer",
		data={"job_description": "Need Python experience."},
		files={"resume": ("resume.docx", b"content", "application/octet-stream")},
	)

	assert response.status_code == 415
	assert "Unsupported resume type" in response.json()["detail"]


def test_answer_rejects_unreadable_resume() -> None:
	response = client.post(
		"/answer",
		data={"job_description": "Need Python experience."},
		files={"resume": ("resume.pdf", b"not a PDF", "application/pdf")},
	)

	assert response.status_code == 400
	assert response.json()["detail"] == "Unable to read the PDF document."


def test_answer_handles_criteria_service_failure(monkeypatch) -> None:
	monkeypatch.setattr(
		criteria_extractor,
		"extract_criteria",
		Mock(side_effect=criteria_extractor.CriteriaExtractionError("provider failure")),
	)

	response = client.post(
		"/answer",
		data={"job_description": "Need Python experience."},
		files={"resume": ("resume.txt", b"Python experience", "text/plain")},
	)

	assert response.status_code == 502
	assert response.json()["detail"] == "Unable to extract job criteria."
