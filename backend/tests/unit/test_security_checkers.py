from __future__ import annotations

import httpx
import pytest

from app.config import settings
from app.services import security_checkers


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code, expected", [(401, "PASS"), (403, "PASS"), (200, "FAIL")])
async def test_authentication_configuration_checker(status_code: int, expected: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ALLOW_PRIVATE_TARGETS", True)

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code)

    original = httpx.AsyncClient
    monkeypatch.setattr(
        security_checkers.httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    result = await security_checkers.check_authentication_configuration("http://127.0.0.1/private")

    assert result["status"] == expected
