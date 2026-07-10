from __future__ import annotations

from app.config import settings
from app.core.llm.openai_compat_client import OpenAICompatClient


def get_agent_llm_client() -> OpenAICompatClient:
    """
    LLM client for the agent (Phi): Playwright script generation, orchestration.

    Uses AGENT_LMSTUDIO_URL if set (second LM Studio instance), else LMSTUDIO_URL.
    Model is chosen via AGENT_LLM_MODEL when calling .chat(model=...).
    """
    base_url = (settings.AGENT_LMSTUDIO_URL or settings.LMSTUDIO_URL).rstrip("/")
    return OpenAICompatClient(base_url=base_url)

