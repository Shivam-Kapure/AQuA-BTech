from __future__ import annotations

import httpx
import pytest

from app.config import settings
from app.models.api_spec import ApiAssertion, ApiTestCase, ApiWorkflowStep
from app.services.api_workflow import execute_api_workflow


@pytest.mark.asyncio
async def test_workflow_passes_extracted_values_to_dependent_step(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ALLOW_PRIVATE_TARGETS", True)
    seen_headers: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(request.headers.get("X-Request-Id", ""))
        return httpx.Response(200, json={"request_id": "abc-123"} if request.url.path == "/setup" else {"ok": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    result = await execute_api_workflow([
        ApiWorkflowStep(
            name="setup",
            test_case=ApiTestCase(name="setup", method="GET", url="http://127.0.0.1/setup", assertions=[ApiAssertion(kind="status", expected=200)]),
            extract={"request_id": "$.request_id"},
        ),
        ApiWorkflowStep(
            name="dependent",
            test_case=ApiTestCase(name="dependent", method="GET", url="http://127.0.0.1/use", headers={"X-Request-Id": "${request_id}"}, assertions=[ApiAssertion(kind="status", expected=200)]),
        ),
    ], client=client)
    await client.aclose()

    assert result["passed"] is True
    assert seen_headers[-1] == "abc-123"
