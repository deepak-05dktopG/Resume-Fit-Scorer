import json

from pydantic import ValidationError

from app.config import ScoringWeights, load_scoring_config
from app.models import Criterion, CriterionScore, CriterionScoringResult, OverallAssessment
from app.services.llm_client import GroqLLMClient, LLMClientError


class ScoringError(ValueError):
	"""Controlled error raised when criterion scoring cannot be completed."""


SYSTEM_PROMPT = """You are a resume evaluation assistant. Evaluate only the specified criterion against the supplied resume.
Use only evidence explicitly present in the resume. Do not infer unsupported skills.
Return a score from 0 to 4 using the provided rubric. Include concise evidence and reasoning.
Return ONLY JSON. Do not include markdown fences.
"""

SCORING_RUBRIC = """0 = No evidence
The resume provides no evidence that the candidate has this skill or experience.

1 = Weak / indirect evidence
The resume provides only weak, indirect, or highly ambiguous evidence.

2 = Partial evidence
The resume shows some relevant knowledge or experience, but it is incomplete or limited.

3 = Strong evidence
The resume clearly demonstrates relevant experience with the criterion.

4 = Direct / highly relevant evidence
The resume demonstrates substantial, direct, and highly relevant experience with the criterion.

Score only evidence present in the resume. Do not infer skills from job titles alone.
Do not assume knowledge because another related skill is present.
Do not reward keywords without meaningful supporting evidence.
Do not penalize the candidate for information that simply isn't present beyond giving the appropriate evidence score.
Do not invent evidence. Evidence must be directly traceable to the resume text."""


llm_client: GroqLLMClient = GroqLLMClient()


def score_resume_against_criteria(
	resume_text: str,
	criteria: list[Criterion],
) -> CriterionScoringResult:
	"""Score each job criterion independently against the supplied resume."""

	if not resume_text.strip():
		raise ScoringError("Resume text cannot be empty.")
	if not criteria:
		raise ScoringError("Criteria cannot be empty.")

	scores: list[CriterionScore] = []
	for criterion in criteria:
		scores.append(_score_criterion(resume_text, criterion))

	return CriterionScoringResult(scores=scores)


def _score_criterion(resume_text: str, criterion: Criterion) -> CriterionScore:
	user_prompt = f"""Evaluate this criterion independently.

Criterion ID: {criterion.id}
Criterion name: {criterion.name}
Criterion description: {criterion.description}

Resume text:
{resume_text}

Scoring rubric:
{SCORING_RUBRIC}

Return exactly this JSON shape:
{{"criterion_id": "{criterion.id}", "score": 0, "evidence": [], "reasoning": "..."}}
Return ONLY JSON. Do not include markdown fences."""

	try:
		response_text = llm_client.complete(SYSTEM_PROMPT, user_prompt)
	except LLMClientError as error:
		raise ScoringError(str(error)) from error

	try:
		response_data = json.loads(response_text)
		score = CriterionScore.model_validate(response_data)
	except (json.JSONDecodeError, TypeError, ValidationError) as error:
		raise ScoringError(
			"The LLM returned an invalid structured scoring response."
		) from error

	if score.criterion_id != criterion.id:
		raise ScoringError("The LLM returned a score for the wrong criterion.")

	return score


def calculate_overall_score(
	criterion_scores: list[CriterionScore],
	criteria: list[Criterion],
	weights: ScoringWeights | None = None,
) -> OverallAssessment:
	"""Calculate a deterministic weighted score from validated criterion scores."""

	if not criteria:
		raise ScoringError("Criteria cannot be empty.")

	configured_weights = weights or load_scoring_config().weights
	criteria_by_id: dict[str, Criterion] = {}
	for criterion in criteria:
		if criterion.id in criteria_by_id:
			raise ScoringError("Criteria contain a duplicate criterion ID.")
		criteria_by_id[criterion.id] = criterion

	scores_by_id: dict[str, CriterionScore] = {}
	for criterion_score in criterion_scores:
		if criterion_score.criterion_id in scores_by_id:
			raise ScoringError("Criterion scores contain a duplicate criterion ID.")
		if criterion_score.criterion_id not in criteria_by_id:
			raise ScoringError("Criterion scores contain an unknown criterion ID.")
		scores_by_id[criterion_score.criterion_id] = criterion_score

	missing_ids = set(criteria_by_id) - set(scores_by_id)
	if missing_ids:
		raise ScoringError("Criterion scores are missing one or more criteria.")

	weight_by_importance = {
		"required": configured_weights.required,
		"preferred": configured_weights.preferred,
	}
	total_weight = 0.0
	weighted_score = 0.0
	for criterion in criteria:
		weight = weight_by_importance.get(criterion.importance.value)
		if weight is None or weight < 0:
			raise ScoringError("Criterion importance has no valid configured weight.")
		total_weight += weight
		weighted_score += (scores_by_id[criterion.id].score / 4) * weight

	if total_weight == 0:
		raise ScoringError("Total applicable scoring weight must be greater than zero.")

	overall_score = round((weighted_score / total_weight) * 100, 2)
	return OverallAssessment(
		overall_score=overall_score,
		criterion_scores=[scores_by_id[criterion.id] for criterion in criteria],
	)
