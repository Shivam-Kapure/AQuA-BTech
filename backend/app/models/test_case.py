from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class TestStep(BaseModel):
    __test__ = False
    action: str
    selector: str | None = None
    value: Any | None = None
    assertion: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None


class TestCaseCreate(BaseModel):
    __test__ = False
    name: str
    url: str
    description: str | None = None
    steps: list[TestStep] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TestCaseInDB(TestCaseCreate):
    __test__ = False
    id: str | None = Field(default=None, alias="_id")
    project_id: str | None = None
    status: Literal["draft", "ready", "archived", "waiting", "passed", "failed"] = "draft"
    failure_reason: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
    }

