from __future__ import annotations

from app.config import settings
from app.core.llm.openai_compat_client import OpenAICompatClient
from app.core.llm.groq_client import get_groq_client
from app.core.llm.lmstudio_client import get_lmstudio_client


def get_llm_client() -> OpenAICompatClient:
    provider = (settings.LLM_PROVIDER or "lmstudio").lower()
    if provider == "groq":
        return get_groq_client()
    return get_lmstudio_client()

