from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings


_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    username: str


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_access_token(*, user_id: str, username: str) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "username": username,
        "iat": now,
        "exp": now + settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }
    encoded_header = _b64encode(json.dumps(header, separators=(",", ":")).encode())
    encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
    message = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(
        settings.AUTH_SECRET_KEY.encode("utf-8"), message, hashlib.sha256
    ).digest()
    return f"{message.decode('ascii')}.{_b64encode(signature)}"


def _decode_access_token(token: str) -> AuthenticatedUser:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        header = json.loads(_b64decode(encoded_header))
        payload = json.loads(_b64decode(encoded_payload))
        if header.get("alg") != "HS256" or header.get("typ") != "JWT":
            raise ValueError("unsupported token header")
        message = f"{encoded_header}.{encoded_payload}".encode("ascii")
        expected = hmac.new(
            settings.AUTH_SECRET_KEY.encode("utf-8"), message, hashlib.sha256
        ).digest()
        if not hmac.compare_digest(_b64decode(encoded_signature), expected):
            raise ValueError("invalid token signature")
        if not isinstance(payload.get("sub"), str) or not payload["sub"]:
            raise ValueError("token subject is missing")
        if not isinstance(payload.get("username"), str) or not payload["username"]:
            raise ValueError("token username is missing")
        if int(payload.get("exp", 0)) <= int(time.time()):
            raise ValueError("token has expired")
        return AuthenticatedUser(id=payload["sub"], username=payload["username"])
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _decode_access_token(credentials.credentials)


def validate_route_jwt(value: str | None) -> str | None:
    """Validate the optional JWT forwarded to the user's target application."""
    if value is None or not value.strip():
        return None
    token = value.strip()
    parts = token.split(".")
    if len(parts) != 3 or len(token) > 8192 or any(not part for part in parts):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="X-Aqua-Route-Jwt must be a compact JWT",
        )
    if any(ord(char) < 32 or ord(char) == 127 for char in token):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="X-Aqua-Route-Jwt contains invalid characters",
        )
    return token


def get_route_jwt(
    value: str | None = Header(default=None, alias="X-Aqua-Route-Jwt"),
) -> str | None:
    """FastAPI dependency for the optional target-application JWT."""
    return validate_route_jwt(value)
