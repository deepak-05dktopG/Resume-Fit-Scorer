import json

from pydantic import ValidationError

from app.models import CriteriaExtraction
from app.services.llm_client import GroqLLMClient, LLMClientError


class CriteriaExtractionError(ValueError):
	"""Controlled error raised when criteria extraction cannot be completed."""


SYSTEM_PROMPT = """You are a structured job-requirement extraction assistant.
Extract only hiring criteria explicitly supported by the job description.
Separate required and preferred criteria, combine duplicate requirements, and keep criteria meaningful and distinct.
Do not assign numeric weights. Return only valid JSON matching this exact schema:
{"criteria": [{"id": "python", "name": "Python", "description": "Experience developing software using Python", "importance": "required"}]}
Criterion IDs must be concise, stable, lowercase, and use underscores where needed.
Do not include markdown fences or explanations outside the JSON. The output will be machine-validated.
"""


llm_client: GroqLLMClient = GroqLLMClient()


def extract_criteria(job_description: str) -> CriteriaExtraction:
	"""Extract and validate structured hiring criteria from a job description."""

	if not job_description.strip():
		raise CriteriaExtractionError("Job description cannot be empty.")

	user_prompt = f"Job description:\n\n{job_description}\n\nReturn only the requested JSON object."

	try:
		response_text = llm_client.complete(SYSTEM_PROMPT, user_prompt)
	except LLMClientError as error:
		raise CriteriaExtractionError(str(error)) from error

	try:
		response_data = json.loads(response_text)
		return CriteriaExtraction.model_validate(response_data)
	except (json.JSONDecodeError, TypeError, ValidationError) as error:
		raise CriteriaExtractionError(
			"The LLM returned an invalid structured criteria response."
		) from error
