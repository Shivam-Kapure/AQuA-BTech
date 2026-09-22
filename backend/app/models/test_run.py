from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

__test__ = False


class RunStatus(str, Enum):
    queued = "queued"
    running = "running"
    waiting = "waiting"
    passed = "passed"
    failed = "failed"
    warning = "warning"
    cancelled = "cancelled"


class ArtifactMetadata(BaseModel):
    id: str | None = None
    owner_id: str
    run_id: str
    kind: str
    storage_key: str
    content_type: str | None = None
    byte_size: int | None = None
    sha256: str | None = None
    redacted: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None


class TestRunRecord(BaseModel):
    id: str | None = None
    owner_id: str
    project_id: str | None = None
    project_name: str | None = None
    test_id: str | None = None
    test_name: str
    status: RunStatus = RunStatus.queued
    duration_ms: float | None = None
    runner_version: str | None = None
    generation_mode: str | None = None
    inputs_ref: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    failure_details: dict[str, Any] | None = None
    correlation_id: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
