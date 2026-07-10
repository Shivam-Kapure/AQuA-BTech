from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol, Sequence

from app.core.llm.types import ChatMessage


@dataclass(frozen=True)
class LLMResult:
    text: str
    raw: dict[str, Any] | None = None

    def json(self) -> Any:
        return json.loads(self.text)


class BaseLLMClient(Protocol):
    async def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResult: ...

