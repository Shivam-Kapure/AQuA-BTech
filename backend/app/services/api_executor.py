from __future__ import annotations

import time
from typing import Any

import httpx
from jsonschema import ValidationError, validate

from app.config import settings
from app.core.url_security import validate_target_url
from app.models.api_spec import ApiAssertion, ApiTestCase


SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie", "x-api-key"}
SENSITIVE_KEYS = {"password", "token", "secret", "authorization", "access_token", "refresh_token"}


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: "[REDACTED]" if key.lower() in SENSITIVE_KEYS else _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _json_path(value: Any, path: str | None) -> Any:
    if not path:
        return value
    for part in path.lstrip("$.").split("."):
        if isinstance(value, dict):
            value = value.get(part)
        elif isinstance(value, list) and part.isdigit():
            value = value[int(part)]
        else:
            return None
    return value


def _check_assertion(assertion: ApiAssertion, response: httpx.Response, body: Any, elapsed_ms: float) -> bool:
    kind = assertion.kind.lower()
    if kind == "status":
        return response.status_code == int(assertion.expected)
    if kind == "header":
        return response.headers.get(assertion.path or "", "") == str(assertion.expected)
    if kind == "json_field":
        return _json_path(body, assertion.path) == assertion.expected
    if kind == "content_type":
        return response.headers.get("content-type", "").split(";", 1)[0].strip() == str(assertion.expected)
    if kind == "response_time_ms":
        return elapsed_ms <= float(assertion.expected)
    if kind == "json_schema":
        try:
            validate(instance=body, schema=assertion.expected)
            return True
        except ValidationError:
            return False
    raise ValueError(f"Unsupported API assertion kind: {assertion.kind}")


async def execute_api_test(test_case: ApiTestCase, *, client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    validate_target_url(test_case.url)
    own_client = client is None
    client = client or httpx.AsyncClient(verify=settings.HTTP_VERIFY_TLS, follow_redirects=False, timeout=30.0)
    started = time.perf_counter()
    try:
        response = await client.request(
            test_case.method.upper(),
            test_case.url,
            headers=test_case.headers,
            params=test_case.query,
            json=test_case.body if isinstance(test_case.body, (dict, list)) else None,
            content=test_case.body if isinstance(test_case.body, str) else None,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        try:
            body = response.json()
        except ValueError:
            body = response.text
        results = []
        for assertion in test_case.assertions:
            passed = _check_assertion(assertion, response, body, elapsed_ms)
            results.append({"kind": assertion.kind, "passed": passed, "path": assertion.path})
        return {
            "passed": all(result["passed"] for result in results),
            "status_code": response.status_code,
            "response_time_ms": round(elapsed_ms, 2),
            "assertions": results,
            "headers": {key: "[REDACTED]" if key.lower() in SENSITIVE_HEADERS else value for key, value in response.headers.items()},
            "body": _redact(body),
        }
    finally:
        if own_client:
            await client.aclose()
