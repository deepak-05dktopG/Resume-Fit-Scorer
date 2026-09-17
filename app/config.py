from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	groq_api_key: str = ""
	llm_model: str = "llama-3.3-70b-versatile"
	llm_temperature: float = 0
	llm_max_tokens: int = 2000

	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		extra="ignore",
	)


settings = Settings()


class ScoringWeights(BaseModel):
	required: float = Field(ge=0)
	preferred: float = Field(ge=0)

	@field_validator("required", "preferred", mode="before")
	@classmethod
	def validate_numeric_weight(cls, value: Any) -> Any:
		if isinstance(value, bool) or not isinstance(value, (int, float)):
			raise ValueError("scoring weights must be numeric")
		return value


class ScoringConfig(BaseModel):
	weights: ScoringWeights


class ScoringConfigError(ValueError):
	"""Raised when the scoring configuration cannot be loaded or validated."""


SCORING_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "scoring.yaml"


def load_scoring_config(path: Path = SCORING_CONFIG_PATH) -> ScoringConfig:
	"""Load and validate scoring weights from the YAML configuration file."""

	try:
		with path.open("r", encoding="utf-8") as config_file:
			config_data = yaml.safe_load(config_file)
		return ScoringConfig.model_validate(config_data)
	except (OSError, yaml.YAMLError, TypeError, ValueError) as error:
		raise ScoringConfigError("Unable to load valid scoring configuration.") from error
