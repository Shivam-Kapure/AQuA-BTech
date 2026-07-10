from __future__ import annotations

from typing import Literal, TypedDict


Role = Literal["system", "user", "assistant", "tool"]


class ChatMessage(TypedDict, total=False):
    role: Role
    content: str
    name: str
    tool_call_id: str

