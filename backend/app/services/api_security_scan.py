from __future__ import annotations

from typing import Any

import httpx
from jsonschema import ValidationError, validate

from app.core.url_security import validate_target_url
from app.models.api_spec import ApiSpec

SENSITIVE_RESPONSE_KEYS = {"password", "passwd", "secret", "token", "access_token", "refresh_token"}
OBJECT_PATH_MARKERS = {"id", "uuid", "key", "user", "account", "order", "item", "resource"}
PRIVILEGED_PATH_MARKERS = {"admin", "manage", "internal", "staff", "moderator"}
BODY_METHODS = {"POST", "PUT", "PATCH"}
FINDING_SEVERITIES = {
    "authentication": "high", "bola_candidate": "high", "bfla_candidate": "high",
    "schema_abuse": "medium", "excessive_data_exposure": "high", "error_leakage": "medium",
    "schema_validation": "medium", "cors": "medium", "rate_limit": "low", "reachability": "low",
}


def _with_severities(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for finding in findings:
        finding["severity"] = FINDING_SEVERITIES.get(finding["category"], "medium")
    return findings


def _sensitive_keys(value: Any, prefix: str = "") -> list[str]:
    if isinstance(value, dict):
        keys: list[str] = []
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if str(key).lower() in SENSITIVE_RESPONSE_KEYS:
                keys.append(path)
            keys.extend(_sensitive_keys(item, path))
        return keys
    if isinstance(value, list):
        keys: list[str] = []
        for index, item in enumerate(value):
            keys.extend(_sensitive_keys(item, f"{prefix}[{index}]"))
        return keys
    return []


def _path_segments(path: str) -> list[str]:
    return [segment.lower() for segment in path.split("/") if segment]


def _static_authorization_findings(operation: Any) -> list[dict[str, Any]]:
    """Identify authorization surfaces for an explicitly authorized active probe later."""
    segments = _path_segments(operation.path)
    normalized_segments = {segment.strip("{}_") for segment in segments}
    has_dynamic_segment = any(segment.startswith("{") and segment.endswith("}") for segment in segments)
    findings: list[dict[str, Any]] = []
    if operation.auth_schemes and (has_dynamic_segment or any(segment in OBJECT_PATH_MARKERS or any(marker in segment for marker in OBJECT_PATH_MARKERS) for segment in normalized_segments)):
        findings.append({
            "operation_id": operation.operation_id,
            "category": "bola_candidate",
            "status": "WARNING",
            "finding": "Object-scoped route requires a multi-principal authorization probe to verify BOLA resistance; no active probe was run.",
        })
    if operation.auth_schemes and (normalized_segments & PRIVILEGED_PATH_MARKERS or operation.method.upper() in {"DELETE", "PATCH"}):
        findings.append({
            "operation_id": operation.operation_id,
            "category": "bfla_candidate",
            "status": "WARNING",
            "finding": "Privileged route requires role-separated authorization testing to verify BFLA resistance; no active probe was run.",
        })
    if operation.method.upper() in BODY_METHODS and operation.request_schema is None:
        findings.append({
            "operation_id": operation.operation_id,
            "category": "schema_abuse",
            "status": "WARNING",
            "finding": "State-changing operation has no declared request schema; malformed and unexpected fields cannot be passively evaluated.",
        })
    elif operation.request_schema and operation.request_schema.get("type") == "object" and operation.request_schema.get("additionalProperties", True):
        findings.append({
            "operation_id": operation.operation_id,
            "category": "schema_abuse",
            "status": "WARNING",
            "finding": "Request schema permits additional properties; review strict input validation for schema-abuse resistance.",
        })
    return findings


async def scan_api_security(
    spec: ApiSpec, *, client: httpx.AsyncClient | None = None, active: bool = False
) -> list[dict[str, Any]]:
    """Run passive checks; active/destructive probes are intentionally opt-in and unsupported here."""
    if active:
        raise ValueError("Active API security probes require an explicit worker policy and are not enabled")
    findings: list[dict[str, Any]] = []
    for operation in spec.operations:
        findings.extend(_static_authorization_findings(operation))
        if not operation.auth_schemes:
            findings.append({"operation_id": operation.operation_id, "category": "authentication", "status": "WARNING", "finding": "No authentication scheme is declared for this operation."})
    if not spec.base_urls:
        return _with_severities(findings)
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
            if not ({"x-ratelimit-limit", "ratelimit-limit"} & {key.lower() for key in response.headers}):
                findings.append({"operation_id": operation.operation_id, "category": "rate_limit", "status": "WARNING", "finding": "No rate-limit policy header was observed."})
            if response.status_code >= 500:
                findings.append({"operation_id": operation.operation_id, "category": "error_leakage", "status": "WARNING", "finding": f"Endpoint returned HTTP {response.status_code} to a passive request."})
            try:
                body = response.json()
            except ValueError:
                body = None
            if operation.response_schema and body is not None:
                try:
                    validate(instance=body, schema=operation.response_schema)
                except ValidationError:
                    findings.append({"operation_id": operation.operation_id, "category": "schema_validation", "status": "WARNING", "finding": "Response did not match the documented response schema."})
            exposed = _sensitive_keys(body)
            if exposed:
                findings.append({"operation_id": operation.operation_id, "category": "excessive_data_exposure", "status": "WARNING", "finding": f"Sensitive-looking response fields observed: {', '.join(exposed[:10])}"})
    finally:
        if own_client:
            await client.aclose()
    return _with_severities(findings)
