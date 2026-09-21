from __future__ import annotations

from typing import Any

import httpx

from app.core.url_security import validate_target_url
from app.models.api_spec import ApiSpec


async def scan_api_security(
    spec: ApiSpec, *, client: httpx.AsyncClient | None = None, active: bool = False
) -> list[dict[str, Any]]:
    """Run passive checks; active/destructive probes are intentionally opt-in and unsupported here."""
    if active:
        raise ValueError("Active API security probes require an explicit worker policy and are not enabled")
    findings: list[dict[str, Any]] = []
    for operation in spec.operations:
        if not operation.auth_schemes:
            findings.append({"operation_id": operation.operation_id, "category": "authentication", "status": "WARNING", "finding": "No authentication scheme is declared for this operation."})
    if not spec.base_urls:
        return findings
    own_client = client is None
    client = client or httpx.AsyncClient(follow_redirects=False, timeout=15.0)
    try:
        for operation in spec.operations:
            url = spec.base_urls[0].rstrip("/") + "/" + operation.path.lstrip("/")
            try:
                validate_target_url(url)
                response = await client.request(operation.method, url)
            except Exception as exc:
                findings.append({"operation_id": operation.operation_id, "category": "reachability", "status": "WARNING", "finding": str(exc)})
                continue
            if "access-control-allow-origin" not in response.headers:
                findings.append({"operation_id": operation.operation_id, "category": "cors", "status": "WARNING", "finding": "No CORS policy header was observed."})
            if response.status_code >= 500:
                findings.append({"operation_id": operation.operation_id, "category": "error_leakage", "status": "WARNING", "finding": f"Endpoint returned HTTP {response.status_code} to a passive request."})
    finally:
        if own_client:
            await client.aclose()
    return findings
