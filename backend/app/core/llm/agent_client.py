from __future__ import annotations

from app.config import settings
from app.core.llm.groq_client import get_groq_client
from app.core.llm.openai_compat_client import OpenAICompatClient


def get_agent_llm_client() -> OpenAICompatClient:
    """
    LLM client for the agent: Playwright script generation, orchestration.

    Uses Groq when LLM_PROVIDER=groq; otherwise AGENT_LMSTUDIO_URL if set
    (second LM Studio instance), else LMSTUDIO_URL.
    Model is chosen via AGENT_LLM_MODEL when calling .chat(model=...).
    """
    if (settings.LLM_PROVIDER or "lmstudio").lower() == "groq":
        return get_groq_client()
    base_url = (settings.AGENT_LMSTUDIO_URL or settings.LMSTUDIO_URL).rstrip("/")
    return OpenAICompatClient(base_url=base_url)
