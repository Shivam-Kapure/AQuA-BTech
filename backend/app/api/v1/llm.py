from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.llm import get_llm_client

router = APIRouter()


class LLMTestRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    system: str | None = None
    want_json: bool = True
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None


@router.post("/test")
async def llm_test(payload: LLMTestRequest) -> dict[str, Any]:
    client = get_llm_client()
    messages: list[dict[str, str]] = []
    if payload.system:
        messages.append({"role": "system", "content": payload.system})
    messages.append({"role": "user", "content": payload.prompt})

    response_format = {"type": "json_object"} if payload.want_json else {"type": "text"}
    res = await client.chat(
        messages,
        model=payload.model,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        response_format=response_format,
    )

    parsed = None
    if payload.want_json:
        try:
            parsed = json.loads(res.text)
        except Exception:
            parsed = None

    return {"text": res.text, "json": parsed}

