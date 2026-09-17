from enum import Enum

from pydantic import BaseModel, Field, field_validator


class CriterionImportance(str, Enum):
	required = "required"
	preferred = "preferred"


class Criterion(BaseModel):
	id: str = Field(min_length=1)
	name: str = Field(min_length=1)
	description: str = Field(min_length=1)
	importance: CriterionImportance

	@field_validator("id")
	@classmethod
	def validate_id(cls, value: str) -> str:
		if value != value.lower() or not value.replace("_", "").isalnum():
			raise ValueError("criterion id must be lowercase and use only letters, numbers, and underscores")
		return value


class CriteriaExtraction(BaseModel):
	criteria: list[Criterion]


class CriterionScore(BaseModel):
	criterion_id: str = Field(min_length=1)
	score: int = Field(strict=True, ge=0, le=4)
	evidence: list[str]
	reasoning: str = Field(min_length=1)


class CriterionScoringResult(BaseModel):
	scores: list[CriterionScore]
