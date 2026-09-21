from __future__ import annotations

import json
from typing import Any

from loguru import logger

from app.core.llm import get_llm_client
from app.db.repositories.project_repo import ProjectRepository
from app.db.repositories.security_test_repo import SecurityTestCaseRepository
from app.models.security_test import SecurityTestCaseCreate, SecurityTestCaseInDB

# Context-aware generation
from app.core.browser.playwright_controller import fetch_page_html
from app.core.browser.dom_parser import extract_interactive_elements, build_dom_context_string

SECURITY_PROMPT_TEMPLATE = """
You are an expert Application Security Engineer and Penetration Tester. 
Analyze the following web application description and its visible DOM elements to generate comprehensive defensive security test cases.

Target URL: {url}

### Available UI Elements on the Page:
{dom_context}

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
    # 1. Scrape the DOM and build context
    html = await fetch_page_html(url)
    elements = extract_interactive_elements(html)
    dom_context = build_dom_context_string(elements)
    
    logger.info(f"Generated DOM context length for security: {len(dom_context)} characters for {url}")

    client = get_llm_client()

    if not project_name:
        raise ValueError("project_name is required to generate security test cases.")

    project_repo = ProjectRepository()
    project = await project_repo.get_or_create_by_name(
        project_name, url=url, owner_id=owner_id
    )
    project_id = project.id

    prompt = SECURITY_PROMPT_TEMPLATE.format(url=url, dom_context=dom_context)
    messages = [
        {
            "role": "system",
            "content": "You generate high-quality JSON security test cases for web applications.",
        },
        {"role": "user", "content": prompt},
    ]

    res = await client.chat(
        messages,
        response_format={"type": "json_object"},
    )

    raw = res.text.strip()

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

    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LLM JSON for security test cases: {e}\nRaw: {raw}") from e

    if not isinstance(parsed, list):
        raise ValueError("LLM response JSON must be an array of security test cases")

    test_case_creates: list[SecurityTestCaseCreate] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue

        try:
            tc = SecurityTestCaseCreate(
                test_id=item.get("test_id", "UNKNOWN"),
                title=item.get("title", "Unnamed Security Test"),
                category=item.get("category", "General"),
                target=item.get("target", url),
                method=item.get("method", ""),
                parameter=item.get("parameter", ""),
                test_type=item.get("test_type", "input_validation"),
                expected_secure_behavior=item.get("expected_secure_behavior", "Secure default"),
                severity=item.get("severity", "low"),
                url=url,
            )
            test_case_creates.append(tc)
        except Exception as parse_e:
            logger.warning(f"Skipping malformed security test case: {parse_e}")

    repo = SecurityTestCaseRepository(project_name=project.name)
    created = await repo.create_many(test_case_creates, project_id=project_id)
    return created
