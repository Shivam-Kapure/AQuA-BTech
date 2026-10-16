from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger
from pydantic import ValidationError

from app.core.llm import get_llm_client
from app.models.api_spec import ApiOperation, ApiSpec, ApiTestCase
from app.services.decision_scoring import score_test_case

_ASSERTION_KINDS = {"status", "header", "json_field", "content_type", "response_time_ms", "json_schema"}
_STATUS_TEXT = re.compile(r"status(?:_code)?\s*(?:==|=|is|:)?\s*(\d{3})", re.IGNORECASE)

PROMPT = """Generate JSON only: an array of at most {count} API test cases for the operations below.

Base URL: {base_url}
Operations (method, path, parameters, request body schema, auth, documented response status codes):
{operations}

Each test case is an object with:
- "name": short description
- "method": HTTP method of one listed operation
- "url": the operation path starting with "/" (fill path parameters with realistic values; no base URL)
- "headers": object (may be empty), "query": object of string values (may be empty)
- "body": JSON object for POST/PUT/PATCH requests, otherwise null
- "assertions": array of objects, each one of:
    {{"kind": "status", "expected": 200}}
    {{"kind": "content_type", "expected": "application/json"}}
    {{"kind": "json_field", "path": "$.field.sub", "expected": <exact value>}}
    {{"kind": "response_time_ms", "expected": 2000}}
- "category": "happy_path" | "edge_case" | "negative_test", "priority": "high" | "medium" | "low"

Rules:
- No authentication token is available. For operations that require auth, test that a request
  without a token is rejected (expect status 401) instead of expecting success.
- Expected status codes must come from the operation's documented "responses" codes.
- Use the documented example values for request bodies where given; only assert values you are certain of.
- Mix happy paths, edge cases and negative tests (missing fields, invalid values, unknown ids).
"""


def _path_pattern(path: str) -> re.Pattern[str]:
    """Regex matching a templated path with its parameters filled in, e.g. /posts/{id} -> /posts/abc."""
    escaped = re.escape(path)
    return re.compile("^" + re.sub(r"\\\{[^/]+?\\\}", r"[^/]+", escaped) + "/?$")


def _match_operation(method: str, url: str, spec: ApiSpec) -> ApiOperation | None:
    path = url
    for base in spec.base_urls:
        if path.startswith(base.rstrip("/")):
            path = path[len(base.rstrip("/")):]
    path = "/" + path.split("?", 1)[0].lstrip("/")
    for operation in spec.operations:
        if operation.method.upper() == method.upper() and _path_pattern(operation.path).match(path):
            return operation
    return None


def _normalize_assertion(raw: Any) -> dict[str, Any] | None:
    """Coerce the shapes LLMs produce ("status == 200", {"type": ...}) into ApiAssertion dicts."""
    if isinstance(raw, str):
        match = _STATUS_TEXT.search(raw)
        return {"kind": "status", "expected": int(match.group(1))} if match else None
    if not isinstance(raw, dict):
        return None
    kind = str(raw.get("kind") or raw.get("type") or "").lower().replace("-", "_")
    kind = {"status_code": "status", "body": "json_field", "json_path": "json_field", "response_time": "response_time_ms"}.get(kind, kind)
    if kind not in _ASSERTION_KINDS:
        return None
    expected = raw.get("expected", raw.get("value"))
    if kind == "status":
        match = re.search(r"\d{3}", str(expected))
        if not match:
            return None
        expected = int(match.group(0))
    return {"kind": kind, "expected": expected, "path": raw.get("path") or raw.get("field")}


def _parse_items(raw: str) -> list[dict[str, Any]]:
    text = raw.strip()
    if "```" in text:
        text = text.split("```", 2)[1].removeprefix("json").strip()
    else:
        first, last = text.find("["), text.rfind("]")
        if first != -1 and last > first and not text.startswith("{"):
            text = text[first : last + 1]
    parsed = json.loads(text)
    if isinstance(parsed, dict):
        parsed = parsed.get("tests") or parsed.get("test_cases") or next(
            (value for value in parsed.values() if isinstance(value, list)), None
        )
    if not isinstance(parsed, list):
        raise ValueError("LLM response must contain an array of API test cases")
    return [item for item in parsed if isinstance(item, dict)]


async def generate_api_test_cases(spec: ApiSpec, *, count: int = 10) -> list[ApiTestCase]:
    count = min(max(count, 1), 50)
    base_url = spec.base_urls[0].rstrip("/") if spec.base_urls else ""
    operations = [
        {
            "method": operation.method,
            "path": operation.path,
            "parameters": operation.parameters,
            "body": operation.request_schema,
            "auth": operation.auth_schemes,
            "responses": operation.response_codes,
        }
        for operation in spec.operations
    ]
    prompt = PROMPT.format(
        count=count,
        base_url=base_url or "(none)",
        operations=json.dumps(operations, separators=(",", ":")),
    )
    messages = [
        {"role": "system", "content": "You generate schema-valid API test cases."},
        {"role": "user", "content": prompt},
    ]
    client = get_llm_client()
    # One self-correction round if the model returns invalid JSON.
    for attempt in range(2):
        response = await client.chat(messages, response_format={"type": "json_object"})
        try:
            items = _parse_items(response.text)
            break
        except json.JSONDecodeError as exc:
            if attempt == 1:
                raise ValueError(f"The LLM returned invalid JSON for API test cases: {exc}") from exc
            logger.warning(f"Invalid JSON for API test cases ({exc}); asking the model to correct it")
            messages = messages + [
                {"role": "assistant", "content": response.text},
                {"role": "user", "content": f"That output is not valid JSON ({exc}). Return ONLY the corrected JSON array."},
            ]

    cases: list[ApiTestCase] = []
    rejected: list[str] = []
    for item in items[:count]:
        method = str(item.get("method") or "").upper()
        url = str(item.get("url") or "")
        operation = _match_operation(method, url, spec)
        if operation is None:
            rejected.append(f"{method} {url}")
            continue
        path = "/" + url.split(base_url, 1)[-1].lstrip("/") if base_url and url.startswith(base_url) else "/" + url.lstrip("/")
        item = {
            **item,
            "method": method,
            "url": f"{base_url}{path}" if base_url else path,
            "headers": {str(k): str(v) for k, v in (item.get("headers") or {}).items()} if isinstance(item.get("headers"), dict) else {},
            "query": {str(k): str(v) for k, v in (item.get("query") or {}).items()} if isinstance(item.get("query"), dict) else {},
            "assertions": [a for a in map(_normalize_assertion, item.get("assertions") or []) if a],
        }
        headers_lower = {key.lower() for key in item["headers"]}
        if operation.auth_schemes and "authorization" not in headers_lower and not item.get("auth_context"):
            # No token is sent, so the API must reject the request before anything else:
            # the only outcome to assert is 401.
            item["assertions"] = [{"kind": "status", "expected": 401}]
        try:
            case = ApiTestCase.model_validate(item)
        except ValidationError as exc:
            rejected.append(f"{method} {url} ({exc.error_count()} validation errors)")
            continue
        priority = item.get("priority") if isinstance(item.get("priority"), str) else ("high" if method not in {"GET", "HEAD", "OPTIONS"} else "medium")
        category = item.get("category") if isinstance(item.get("category"), str) else "api"
        score, factors = score_test_case(
            priority=priority,
            category=category,
            step_count=max(1, len(case.assertions)),
        )
        cases.append(case.model_copy(update={"decision_score": score, "decision_score_factors": factors}))

    if rejected:
        logger.warning(f"Skipped {len(rejected)} generated API cases: {rejected}")
    if not cases:
        raise ValueError(f"Generated case does not match an imported operation: {', '.join(rejected) or 'no cases returned'}")
    return cases
