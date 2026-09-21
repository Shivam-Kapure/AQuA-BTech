from __future__ import annotations

import httpx
import pytest

from app.config import settings
from app.models.api_spec import ApiAssertion, ApiTestCase
from app.services.api_executor import execute_api_test


@pytest.mark.asyncio
async def test_execute_api_test_asserts_and_redacts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ALLOW_PRIVATE_TARGETS", True)

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "application/json", "set-cookie": "sid=secret"}, json={"ok": True, "token": "hidden"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    result = await execute_api_test(ApiTestCase(
        name="health",
        method="GET",
        url="http://127.0.0.1/health",
        assertions=[
            ApiAssertion(kind="status", expected=200),
            ApiAssertion(kind="json_field", path="$.ok", expected=True),
            ApiAssertion(kind="content_type", expected="application/json"),
            ApiAssertion(kind="json_schema", expected={"type": "object", "required": ["ok"]}),
        ],
    ), client=client)
    await client.aclose()

    assert result["passed"] is True
    assert result["body"]["token"] == "[REDACTED]"
    assert result["headers"]["set-cookie"] == "[REDACTED]"
