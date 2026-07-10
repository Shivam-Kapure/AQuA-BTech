from __future__ import annotations

from typing import Any, Sequence

import httpx

from app.config import settings
from app.core.llm.base import LLMResult
from app.core.llm.types import ChatMessage


class OpenAICompatClient:
    """
    Minimal OpenAI-compatible Chat Completions client.

    Works with:
    - LM Studio: base_url like http://localhost:1234 (uses /v1/chat/completions)
    - Groq: base_url https://api.groq.com/openai/v1
    """

    def __init__(self, *, base_url: str, api_key: str | None = None):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResult:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload: dict[str, Any] = {
            "model": model or settings.LLM_MODEL,
            "messages": list(messages),
            "temperature": settings.LLM_TEMPERATURE if temperature is None else temperature,
        }
        if max_tokens is None:
            if settings.LLM_MAX_TOKENS is not None:
                payload["max_tokens"] = settings.LLM_MAX_TOKENS
        else:
            payload["max_tokens"] = max_tokens

        if response_format is not None:
            # LM Studio's OpenAI-compat server (as of current builds) accepts:
            # - {"type": "text"}
            # - {"type": "json_schema", "json_schema": {...}}
            # Some other providers accept {"type": "json_object"}.
            rf_type = response_format.get("type")
            if rf_type == "json_object":
                payload["response_format"] = {"type": "text"}
            else:
                payload["response_format"] = response_format

        timeout = httpx.Timeout(settings.LLM_TIMEOUT_S)
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                f"{self._base_url}/v1/chat/completions", json=payload, headers=headers
            )
            try:
                r.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise httpx.HTTPStatusError(
                    f"{e}. Response body: {r.text}",
                    request=e.request,
                    response=e.response,
                ) from None
            data = r.json()

        text = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        return LLMResult(text=text or "", raw=data)

