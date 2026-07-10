from __future__ import annotations

from app.config import settings
from app.core.llm.openai_compat_client import OpenAICompatClient


def get_groq_client() -> OpenAICompatClient:
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set")
    return OpenAICompatClient(
        base_url="https://api.groq.com/openai",
        api_key=settings.GROQ_API_KEY,
    )

