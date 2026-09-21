from __future__ import annotations

import httpx
import pytest

from app.config import settings
from app.models.api_spec import ApiSpec
from app.services.api_security_scan import scan_api_security


@pytest.mark.asyncio
async def test_passive_scan_reports_auth_and_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ALLOW_PRIVATE_TARGETS", True)

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"password": "secret"})

    spec = ApiSpec(title="Demo", version="1", openapi_version="3.0.3", base_urls=["http://127.0.0.1"], operations=[{"operation_id": "get", "method": "GET", "path": "/items"}])
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    findings = await scan_api_security(spec, client=client)
    await client.aclose()

    assert {finding["category"] for finding in findings} == {"authentication", "cors", "rate_limit", "excessive_data_exposure"}


@pytest.mark.asyncio
async def test_active_scan_is_rejected() -> None:
    spec = ApiSpec(title="Demo", version="1", openapi_version="3.0.3")
    with pytest.raises(ValueError, match="Active"):
        await scan_api_security(spec, active=True)
