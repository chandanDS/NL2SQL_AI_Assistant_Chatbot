from functools import lru_cache

from openai import AsyncOpenAI

from backend.core.config import get_settings


@lru_cache
def get_openai_client() -> AsyncOpenAI:
    settings = get_settings()
    api_key = settings.openai_api_key.get_secret_value()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return AsyncOpenAI(api_key=api_key, timeout=settings.openai_timeout_seconds, max_retries=2)
