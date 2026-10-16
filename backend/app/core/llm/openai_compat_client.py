from __future__ import annotations

import asyncio
import re
import time
from typing import Any, Sequence

import httpx

from loguru import logger

from app.config import settings
from app.core.llm.base import LLMResult
from app.core.llm.rate_limits import MAX_WAIT_S, is_daily_limit, retry_delay_s
from app.core.llm.types import ChatMessage

_MAX_RATE_LIMIT_RETRIES = 12
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)
_semaphores: dict[int, asyncio.Semaphore] = {}


def _llm_slot() -> asyncio.Semaphore:
    """Process-wide cap on in-flight LLM requests (one semaphore per event loop)."""
    loop_id = id(asyncio.get_running_loop())
    if loop_id not in _semaphores:
        _semaphores[loop_id] = asyncio.Semaphore(max(1, settings.LLM_MAX_CONCURRENCY))
    return _semaphores[loop_id]
# model -> monotonic time until which it is known to be over its daily cap
_exhausted_until: dict[str, float] = {}


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
        reasoning_effort: str | None = None,
    ) -> LLMResult:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        # Primary model first, then LLM_FALLBACK_MODEL (comma-separated chain), skipping
        # models already known to be over their daily cap.
        chain = [model or settings.LLM_MODEL] + [
            name.strip() for name in (settings.LLM_FALLBACK_MODEL or "").split(",") if name.strip()
        ]
        candidates = [name for name in dict.fromkeys(chain) if _exhausted_until.get(name, 0) <= time.monotonic()]
        requested_model = candidates[0] if candidates else chain[0]
        payload: dict[str, Any] = {
            "model": requested_model,
            "messages": list(messages),
            "temperature": settings.LLM_TEMPERATURE if temperature is None else temperature,
        }
        if max_tokens is None:
            if settings.LLM_MAX_TOKENS is not None:
                payload["max_tokens"] = settings.LLM_MAX_TOKENS
        else:
            payload["max_tokens"] = max_tokens

        effort = reasoning_effort or settings.LLM_REASONING_EFFORT
        if effort and "gpt-oss" in str(payload["model"]):
            # Only reasoning models accept this; it trims hidden reasoning tokens.
            payload["reasoning_effort"] = effort

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
            # Free-tier providers (e.g. Groq) cap tokens per minute and per day. Short
            # per-minute waits are retried; a daily cap (or long wait) switches to
            # LLM_FALLBACK_MODEL when configured instead of blocking or failing.
            for attempt in range(_MAX_RATE_LIMIT_RETRIES + 1):
                async with _llm_slot():
                    r = await client.post(
                        f"{self._base_url}/v1/chat/completions", json=payload, headers=headers
                    )
                if r.status_code != 429:
                    break
                delay = retry_delay_s(r.text, r.headers)
                if is_daily_limit(r.text) or (delay or 0) > MAX_WAIT_S:
                    _exhausted_until[payload["model"]] = time.monotonic() + min(delay or 600.0, 3600.0)
                    remaining = [name for name in dict.fromkeys(chain) if _exhausted_until.get(name, 0) <= time.monotonic()]
                    if remaining:
                        logger.warning(f"{payload['model']} is rate-limited ({r.text[:160]}); switching to {remaining[0]}")
                        payload["model"] = remaining[0]
                        if "gpt-oss" not in remaining[0]:
                            payload.pop("reasoning_effort", None)
                        elif effort:
                            payload["reasoning_effort"] = effort
                        continue
                    break
                if attempt == _MAX_RATE_LIMIT_RETRIES:
                    break
                await asyncio.sleep(min((delay or 5.0) + 0.5, MAX_WAIT_S))
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
        # Some reasoning models inline their thinking; it is never part of the answer.
        text = _THINK_BLOCK.sub("", text or "").strip()
        return LLMResult(text=text, raw=data)

