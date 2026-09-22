"""Validation helpers for user-supplied target URLs."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

from fastapi import HTTPException, status

from app.config import settings


def validate_target_url(url: str) -> str:
    """Validate a target before browser or HTTP access.

    Private address access is opt-in for local development. Callers must
    validate every navigation/request, including any redirect target they
    choose to follow.
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Target URL must use http or https")
    if parsed.username or parsed.password:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Target URL must not contain credentials")

    allowlist = {host.strip().lower() for host in settings.TARGET_HOST_ALLOWLIST.split(",") if host.strip()}
    hostname = parsed.hostname.lower().rstrip(".")
    if allowlist and hostname not in allowlist:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Target host is not allow-listed")

    if not settings.ALLOW_PRIVATE_TARGETS:
        try:
            addresses = {
                info[4][0]
                for info in socket.getaddrinfo(
                    hostname,
                    parsed.port or (443 if parsed.scheme == "https" else 80),
                    type=socket.SOCK_STREAM,
                )
            }
        except socket.gaierror as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Target host could not be resolved") from exc
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Target resolves to a private or reserved address")
    return url


def validate_redirect_target(request_url: str, location: str) -> str:
    """Resolve and validate a redirect before a caller elects to follow it.

    HTTP clients used by AQUA deliberately disable automatic redirects.  This
    helper keeps that policy explicit when a caller needs a single, audited
    redirect hop (for example, a hosted OpenAPI document).
    """
    target = urljoin(request_url, location)
    return validate_target_url(target)
