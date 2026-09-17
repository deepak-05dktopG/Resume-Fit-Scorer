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
