import asyncio

import pytest

from app.models.test_run import RunStatus
from app.services.job_queue import AsyncJobQueue


@pytest.mark.asyncio
async def test_job_queue_retries_and_completes() -> None:
    queue = AsyncJobQueue()
    attempts = 0

    async def factory() -> dict[str, bool]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("temporary")
        return {"passed": True}

    job = await queue.submit(factory, max_retries=1)
    completed = await queue.wait(job.id)

    assert completed.status == RunStatus.passed
    assert completed.attempts == 2


@pytest.mark.asyncio
async def test_job_queue_times_out() -> None:
    queue = AsyncJobQueue()

    async def factory() -> dict[str, bool]:
        await asyncio.sleep(0.05)
        return {"passed": True}

    job = await queue.submit(factory, timeout_seconds=0.001)
    completed = await queue.wait(job.id)

    assert completed.status == RunStatus.failed
    assert completed.error


@pytest.mark.asyncio
async def test_job_queue_can_cancel_running_job() -> None:
    queue = AsyncJobQueue()

    async def factory() -> dict[str, bool]:
        await asyncio.sleep(1)
        return {"passed": True}

    job = await queue.submit(factory)
    await asyncio.sleep(0)
    cancelled = await queue.cancel(job.id)

    assert cancelled is not None
    assert cancelled.status == RunStatus.cancelled


@pytest.mark.asyncio
async def test_job_queue_preserves_warning_status_from_worker() -> None:
    queue = AsyncJobQueue()

    async def factory() -> dict[str, str | bool]:
        return {"passed": False, "status": "warning"}

    job = await queue.submit(factory)
    completed = await queue.wait(job.id)

    assert completed.status == RunStatus.warning
