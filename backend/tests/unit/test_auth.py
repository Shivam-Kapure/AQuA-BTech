from __future__ import annotations

import base64
import json

import pytest
from fastapi import HTTPException

from app.api.v1.auth import _hash_password, _verify_password
from app.config import settings
from app.core import auth


def test_password_hash_is_bcrypt_and_verifies() -> None:
    password_hash = _hash_password("correct horse battery staple")

    assert password_hash.startswith("$2")
    assert _verify_password("correct horse battery staple", password_hash)
    assert not _verify_password("wrong password", password_hash)


def test_access_token_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AUTH_SECRET_KEY", "unit-test-secret")
    token = auth.create_access_token(user_id="user-123", username="alice")

    claims = auth._decode_access_token(token)

    assert claims.id == "user-123"
    assert claims.username == "alice"


def test_access_token_rejects_tampering(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AUTH_SECRET_KEY", "unit-test-secret")
    token = auth.create_access_token(user_id="user-123", username="alice")
    header, payload, _signature = token.split(".")
    encoded = base64.urlsafe_b64encode(
        json.dumps({"sub": "other-user", "username": "mallory", "iat": 1, "exp": 2}).encode()
    ).decode().rstrip("=")

    with pytest.raises(HTTPException) as error:
        auth._decode_access_token(f"{header}.{encoded}.{_signature}")

    assert error.value.status_code == 401


def test_expired_access_token_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AUTH_SECRET_KEY", "unit-test-secret")
    monkeypatch.setattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 0)
    token = auth.create_access_token(user_id="user-123", username="alice")

    with pytest.raises(HTTPException) as error:
        auth._decode_access_token(token)

    assert error.value.status_code == 401
