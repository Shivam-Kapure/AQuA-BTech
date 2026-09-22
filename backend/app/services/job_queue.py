from __future__ import annotations

import asyncio
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable

from app.models.test_run import RunStatus


JobFactory = Callable[[], Awaitable[dict[str, Any]]]


@dataclass
class JobRecord:
    id: str
    owner_id: str | None = None
    status: RunStatus = RunStatus.queued
    attempts: int = 0
    max_retries: int = 0
    timeout_seconds: float = 30.0
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class AsyncJobQueue:
    """Small process-local worker boundary until a distributed broker is selected."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def submit(
        self,
        factory: JobFactory,
        *,
        timeout_seconds: float = 30.0,
        max_retries: int = 0,
        job_id: str | None = None,
        owner_id: str | None = None,
    ) -> JobRecord:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        record = JobRecord(
            id=job_id or str(uuid.uuid4()),
            owner_id=owner_id,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
        self._jobs[record.id] = record
        self._tasks[record.id] = asyncio.create_task(self._run(record, factory))
        return record

    async def _run(self, record: JobRecord, factory: JobFactory) -> None:
        record.status = RunStatus.running
        record.started_at = datetime.utcnow()
        try:
            while record.attempts <= record.max_retries:
                record.attempts += 1
                try:
                    record.result = await asyncio.wait_for(factory(), timeout=record.timeout_seconds)
                    explicit_status = record.result.get("status")
                    if explicit_status in {status.value for status in RunStatus}:
                        record.status = RunStatus(explicit_status)
                    else:
                        record.status = RunStatus.passed if record.result.get("passed", True) else RunStatus.failed
                    return
                except asyncio.CancelledError:
                    record.status = RunStatus.cancelled
                    raise
                except asyncio.TimeoutError:
                    record.error = f"Job timed out after {record.timeout_seconds:.3f}s"
                    if record.attempts > record.max_retries:
                        record.status = RunStatus.failed
                        return
                except Exception as exc:  # retryable worker failure
                    record.error = str(exc)
                    if record.attempts > record.max_retries:
                        record.status = RunStatus.failed
                        return
        finally:
            record.completed_at = datetime.utcnow()

    def get(self, job_id: str) -> JobRecord | None:
        return self._jobs.get(job_id)

    async def wait(self, job_id: str) -> JobRecord:
        task = self._tasks.get(job_id)
        record = self._jobs.get(job_id)
        if task is None or record is None:
            raise KeyError(job_id)
        try:
            await task
        except asyncio.CancelledError:
            pass
        return record

    async def cancel(self, job_id: str) -> JobRecord | None:
        record = self._jobs.get(job_id)
        task = self._tasks.get(job_id)
        if record is None or task is None:
            return None
        if not task.done():
            task.cancel()
            await self.wait(job_id)
        return record


job_queue = AsyncJobQueue()
