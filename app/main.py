from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from app.config import ScoringConfigError
from app.models import AnswerResponse, CriterionAssessment
from app.services import criteria_extractor, parser, scorer
from app.services.criteria_extractor import CriteriaExtractionError
from app.services.scorer import ScoringError


app = FastAPI(
	title="Resume to Job-Description Fit Scorer",
	description="An explainable API for evaluating resume fit against job descriptions.",
)


@app.get("/health")
def health_check() -> dict[str, str]:
	return {
		"status": "ok",
		"service": "resume-fit-scorer",
	}


@app.post("/answer", response_model=AnswerResponse)
async def answer(
	job_description: str = Form(...),
	resume: UploadFile = File(...),
) -> AnswerResponse:
	if not job_description.strip():
		raise HTTPException(status_code=422, detail="Job description cannot be empty.")

	filename = resume.filename or ""
	file_type = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
	if file_type not in {"pdf", "txt"}:
		raise HTTPException(
			status_code=415,
			detail="Unsupported resume type. Only .pdf and .txt files are supported.",
		)

	parsed_resume = parser.parse_document(await resume.read(), filename)
	if not parsed_resume.success:
		raise HTTPException(
			status_code=400,
			detail=parsed_resume.error or "Unable to parse the resume.",
		)

	try:
		criteria_extraction = criteria_extractor.extract_criteria(job_description)
		criterion_result = scorer.score_resume_against_criteria(
			parsed_resume.text,
			criteria_extraction.criteria,
		)
		assessment = scorer.calculate_overall_score(
			criterion_result.scores,
			criteria_extraction.criteria,
		)
	except CriteriaExtractionError as error:
		raise HTTPException(
			status_code=502,
			detail="Unable to extract job criteria.",
		) from error
	except ScoringError as error:
		raise HTTPException(
			status_code=502,
			detail="Unable to score the resume against the job criteria.",
		) from error
	except ScoringConfigError as error:
		raise HTTPException(
			status_code=500,
			detail="Scoring configuration is unavailable.",
		) from error

	scores_by_id = {score.criterion_id: score for score in assessment.criterion_scores}
	return AnswerResponse(
		overall_score=assessment.overall_score,
		criteria=[
			CriterionAssessment(
				id=criterion.id,
				name=criterion.name,
				importance=criterion.importance,
				score=scores_by_id[criterion.id].score,
				evidence=scores_by_id[criterion.id].evidence,
				reasoning=scores_by_id[criterion.id].reasoning,
			)
			for criterion in criteria_extraction.criteria
		],
	)
