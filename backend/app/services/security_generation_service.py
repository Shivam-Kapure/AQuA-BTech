from __future__ import annotations

import json
from typing import Any
from urllib.parse import urljoin

import httpx

from loguru import logger

from app.core.llm import get_llm_client
from app.db.repositories.project_repo import ProjectRepository
from app.db.repositories.security_test_repo import SecurityTestCaseRepository
from app.models.security_test import SecurityTestCaseCreate, SecurityTestCaseInDB
from app.services.decision_scoring import score_test_case

# Context-aware generation
from app.core.browser.playwright_controller import fetch_page_html
from app.core.browser.dom_parser import build_dom_context_string, extract_interactive_elements, page_text_excerpt
from app.core.url_security import validate_target_url
from app.services.openapi_parser import parse_openapi_document

SUPPORTED_TEST_TYPES = {
    "security_headers", "cookie_security", "input_validation", "authentication_configuration", "information_disclosure",
}
_TEST_TYPE_ALIASES = {
    "headers": "security_headers", "security_header": "security_headers", "http_headers": "security_headers",
    "cookies": "cookie_security", "cookie": "cookie_security",
    "xss": "input_validation", "injection": "input_validation", "input": "input_validation", "validation": "input_validation",
    "authentication": "authentication_configuration", "auth": "authentication_configuration", "access_control": "authentication_configuration",
    "information_leakage": "information_disclosure", "disclosure": "information_disclosure",
}


def _normalize_test_type(value: Any) -> str:
    key = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    return key if key in SUPPORTED_TEST_TYPES else _TEST_TYPE_ALIASES.get(key, "input_validation")


async def _api_endpoint_hints(url: str) -> str:
    """List the site's API endpoints (from a published OpenAPI document) so auth checks can target them."""
    for candidate in ("/openapi.json", "/swagger.json"):
        spec_url = urljoin(url, candidate)
        try:
            validate_target_url(spec_url)
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
                response = await client.get(spec_url)
            if response.status_code != 200:
                continue
            spec = parse_openapi_document(response.text)
        except Exception:
            continue
        lines = [
            f"- {op.method} {op.path} ({'requires authentication' if op.auth_schemes else 'public'})"
            for op in spec.operations
        ]
        return "### API endpoints published by this site\n" + "\n".join(lines) + "\n"
    return ""

SECURITY_PROMPT_TEMPLATE = """
You are an expert Application Security Engineer and Penetration Tester. 
Analyze the following web application description and its visible DOM elements to generate comprehensive defensive security test cases.

Target URL: {url}

### Available UI Elements on the Page:
{dom_context}

### Visible page text (excerpt)
{page_text}

Treat facts stated in this text as authoritative: demo/test credentials, rules, limits and the exact
wording of messages it mentions. Use them in steps and expected results instead of guessing.

{api_hints}
Rules for "target":
- Use a full URL on this site or a path starting with "/" (for example an API endpoint above). Never a description.
- authentication_configuration tests must target an endpoint that should require sign-in (from the list above when available); public pages are expected to be reachable anonymously.
- input_validation tests: target the endpoint that receives the input, method GET or POST, and the parameter name.

## Your Task
Generate 5 high-quality security test cases appropriate for this page, ONLY using the elements provided above and understanding the context of the page.
DO NOT generate arbitrary exploit payloads. Focus on defensive validation and configuration checks.

Supported test types are strictly limited to:
- security_headers
- cookie_security
- input_validation
- authentication_configuration
- information_disclosure

For each test case, provide:
- test_id: Unique identifier (e.g., SEC001)
- title: Descriptive name
- category: Security category
- target: Target URL, endpoint, or specific form/element
- method: HTTP method or action (e.g., GET, POST, Submit)
- parameter: Target parameter or field if applicable (e.g., "username")
- test_type: One of the supported test types
- expected_secure_behavior: What the secure behavior should be (e.g., "Should reject scripts", "Should use HttpOnly")
- severity: One of "high", "medium", "low"

Return ONLY a valid JSON array of test case objects, no extra text, no explanations.
""".strip()


async def generate_security_tests_for_url(
    url: str,
    *,
    project_name: str | None = None,
    owner_id: str | None = None,
) -> list[SecurityTestCaseInDB]:
    """
    Use the configured LLM to generate security test cases for a URL
    and persist them to MongoDB.
    """
    if not project_name:
        raise ValueError("project_name is required to generate security test cases.")

    project_repo = ProjectRepository()
    project = await project_repo.get_or_create_by_name(
        project_name, url=url, owner_id=owner_id
    )
    project_id = project.id
    repo = SecurityTestCaseRepository(project_name=project.name)
    existing = await repo.list(project_id=project_id)
    if existing:
        logger.info(f"Reusing {len(existing)} existing security tests for project {project.name}")
        return existing

    # 1. Scrape the DOM and build context
    html = await fetch_page_html(url)
    elements = extract_interactive_elements(html)
    dom_context = build_dom_context_string(elements)
    
    logger.info(f"Generated DOM context length for security: {len(dom_context)} characters for {url}")

    client = get_llm_client()

    prompt = SECURITY_PROMPT_TEMPLATE.format(
        url=url,
        dom_context=dom_context,
        page_text=page_text_excerpt(html) or "(no visible text)",
        api_hints=await _api_endpoint_hints(url),
    )
    messages = [
        {
            "role": "system",
            "content": "You generate high-quality JSON security test cases for web applications.",
        },
        {"role": "user", "content": prompt},
    ]

    for attempt in range(2):
        res = await client.chat(
            messages,
            response_format={"type": "json_object"},
        )
        raw = res.text.strip()
        try:
            parsed = _parse_cases(raw)
            break
        except json.JSONDecodeError as e:
            if attempt == 1:
                raise ValueError(f"Failed to parse LLM JSON for security test cases: {e}\nRaw: {raw}") from e
            logger.warning(f"Invalid JSON for security test cases ({e}); asking the model to correct it")
            messages = messages + [
                {"role": "assistant", "content": raw},
                {"role": "user", "content": f"That output is not valid JSON ({e}). Return ONLY the corrected JSON array."},
            ]

    test_case_creates: list[SecurityTestCaseCreate] = []
    for index, item in enumerate(parsed, start=1):
        if not isinstance(item, dict):
            continue

        try:
            severity = str(item.get("severity", "low")).lower()
            if severity not in {"high", "medium", "low"}:
                severity = "medium"
            score, factors = score_test_case(
                priority=severity,
                category=item.get("category", "General"),
                severity=severity,
                step_count=1,
            )
            tc = SecurityTestCaseCreate(
                # Our own sequential IDs: runs look tests up by test_id, so they must be unique.
                test_id=f"SEC{index:03d}",
                title=item.get("title", "Unnamed Security Test"),
                category=item.get("category", "General"),
                target=str(item.get("target") or url),
                method=str(item.get("method") or "GET"),
                parameter=str(item.get("parameter") or ""),
                test_type=_normalize_test_type(item.get("test_type")),
                expected_secure_behavior=item.get("expected_secure_behavior", "Secure default"),
                severity=severity,
                decision_score=score,
                decision_score_factors=factors,
                url=url,
            )
            test_case_creates.append(tc)
        except Exception as parse_e:
            logger.warning(f"Skipping malformed security test case: {parse_e}")

    created = await repo.create_many(test_case_creates, project_id=project_id)
    return created


def _parse_cases(raw: str) -> list[Any]:
    """Extract the JSON array of security cases from an LLM reply."""
    json_str = raw
    if "```" in raw:
        start = raw.find("```json")
        if start == -1:
            start = raw.find("```")
            start += 3
        else:
            start += len("```json")
        end = raw.find("```", start)
        if end != -1:
            json_str = raw[start:end].strip()
    else:
        first = raw.find("[")
        last = raw.rfind("]")
        if first != -1 and last != -1 and last > first:
            json_str = raw[first : last + 1]

    parsed = json.loads(json_str)
    if isinstance(parsed, dict):
        parsed = next((value for value in parsed.values() if isinstance(value, list)), [parsed])
    if not isinstance(parsed, list):
        raise json.JSONDecodeError("Expected a JSON array of security test cases", json_str, 0)
    return parsed
