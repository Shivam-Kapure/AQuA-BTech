from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    name: str
    url: str | None = None
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectCreate(ProjectBase):
    pass


class ProjectInDB(ProjectBase):
    id: str | None = Field(default=None, alias="_id")
    # Optional for backwards compatibility with pre-ownership documents. New
    # writes always populate this field and scoped queries exclude legacy rows.
    owner_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
    }
