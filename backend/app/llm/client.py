from functools import lru_cache

from openai import AsyncOpenAI

from app.core.config import settings


@lru_cache
def get_llm_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
