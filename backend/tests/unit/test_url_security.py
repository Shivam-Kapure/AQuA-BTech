from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.config import settings
from app.core.url_security import validate_target_url


def test_target_url_requires_http_scheme() -> None:
    with pytest.raises(HTTPException):
        validate_target_url("file:///etc/passwd")


def test_target_url_blocks_private_addresses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ALLOW_PRIVATE_TARGETS", False)
    with pytest.raises(HTTPException):
        validate_target_url("http://127.0.0.1:8080")


def test_target_url_allows_private_addresses_only_when_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ALLOW_PRIVATE_TARGETS", True)
    assert validate_target_url("http://127.0.0.1:8080") == "http://127.0.0.1:8080"


def test_redirect_target_is_resolved_before_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.url_security import validate_redirect_target

    monkeypatch.setattr(settings, "ALLOW_PRIVATE_TARGETS", True)
    assert validate_redirect_target("https://example.com/spec.json", "/next.json") == "https://example.com/next.json"


def test_redirect_target_rejects_disallowed_scheme() -> None:
    from app.core.url_security import validate_redirect_target

    with pytest.raises(HTTPException):
        validate_redirect_target("https://example.com/spec.json", "file:///etc/passwd")
