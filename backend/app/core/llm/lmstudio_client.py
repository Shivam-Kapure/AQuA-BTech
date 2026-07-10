from __future__ import annotations

from app.config import settings
from app.core.llm.openai_compat_client import OpenAICompatClient


def get_lmstudio_client() -> OpenAICompatClient:
    return OpenAICompatClient(base_url=settings.LMSTUDIO_URL)

