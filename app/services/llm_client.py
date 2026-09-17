from groq import APIConnectionError, APIError, APITimeoutError, Groq, RateLimitError

from app.config import settings


class LLMClientError(RuntimeError):
	"""Controlled error raised when the configured LLM cannot be used."""


class GroqLLMClient:
	def complete(self, system_prompt: str, user_prompt: str) -> str:
		if not settings.groq_api_key:
			raise LLMClientError("GROQ_API_KEY is not configured.")

		try:
			client = Groq(api_key=settings.groq_api_key)
			response = client.chat.completions.create(
				model=settings.llm_model,
				messages=[
					{"role": "system", "content": system_prompt},
					{"role": "user", "content": user_prompt},
				],
				temperature=settings.llm_temperature,
				max_tokens=settings.llm_max_tokens,
			)
		except RateLimitError as error:
			raise LLMClientError("The Groq API rate limit was exceeded.") from error
		except APITimeoutError as error:
			raise LLMClientError("The Groq API request timed out.") from error
		except APIConnectionError as error:
			raise LLMClientError("The Groq API could not be reached.") from error
		except APIError as error:
			raise LLMClientError("The Groq API returned an error.") from error

		content = response.choices[0].message.content
		if not content:
			raise LLMClientError("The Groq API returned an empty response.")
		return content


llm_client = GroqLLMClient()
