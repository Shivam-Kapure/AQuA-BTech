from __future__ import annotations

import json
from typing import Any

from app.core.llm import get_llm_client
from app.db.repositories.project_repo import ProjectRepository
from app.db.repositories.test_case_repo import TestCaseRepository
from app.models.test_case import TestCaseCreate, TestStep, TestCaseInDB

# New imports for context-aware generation
from app.core.browser.playwright_controller import fetch_page_html
from app.core.browser.dom_parser import extract_interactive_elements, build_dom_context_string
from app.core.rag.knowledge_manager import KnowledgeManager
from loguru import logger

PROMPT_TEMPLATE = """
You are an expert QA automation engineer. Analyze the following web application description and its visible DOM elements to generate comprehensive test cases.

Target URL: {url}

### Available UI Elements on the Page:
{dom_context}

## Your Task
Generate 5 high‑quality test cases that would be appropriate for this page, ONLY using the elements provided above. DO NOT guess element IDs or classes that are not listed above. Include:
1. Happy path tests (things that should work normally)
2. Edge cases (boundary conditions, unusual inputs)
3. Negative tests (error handling, validation failures)

For each test case, provide:
- test_id: Unique identifier (e.g., TC001)
- test_name: Descriptive name
- category: one of "happy_path", "edge_case", "negative_test"
- priority: one of "high", "medium", "low"
- description: What the test does
- steps: Detailed step‑by‑step actions as an array of short strings
- expected_result: What should happen

Return ONLY a valid JSON array of test case objects, no extra text, no explanations.
""".strip()


async def generate_test_cases_for_url(
    url: str,
    *,
    project_name: str | None = None,
) -> list[TestCaseInDB]:
    """
    Use the configured LLM to generate test cases for a URL
    and persist them to MongoDB. Scrapes the page first to provide context.
    """
    # 1. Scrape the DOM and build context
    html = await fetch_page_html(url)
    elements = extract_interactive_elements(html)
    dom_context = build_dom_context_string(elements)
    
    # 2. Ingest into RAG for playwright generator to use later
    km = KnowledgeManager()
    if elements:
        km.ingest_elements(url, elements)

    logger.info(f"Generated DOM context length: {len(dom_context)} characters for {url}")

    client = get_llm_client()

    if not project_name:
        raise ValueError("project_name is required to generate test cases.")

    project_repo = ProjectRepository()
    project = await project_repo.get_or_create_by_name(project_name, url=url)
    project_id = project.id

    prompt = PROMPT_TEMPLATE.format(url=url, dom_context=dom_context)
    messages = [
        {
            "role": "system",
            "content": "You generate high-quality JSON test cases for web applications.",
        },
        {"role": "user", "content": prompt},
    ]

    res = await client.chat(
        messages,
        response_format={"type": "json_object"},
    )

    raw = res.text.strip()

    # Try to robustly extract the JSON array (handles ```json fences, etc.)
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
        raise ValueError(f"Failed to parse LLM JSON for test cases: {e}\nRaw: {raw}") from e

    if not isinstance(parsed, list):
        raise ValueError("LLM response JSON must be an array of test cases")

    test_case_creates: list[TestCaseCreate] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        name = item.get("test_name") or item.get("name") or "Unnamed test"
        description = item.get("description") or ""
        steps_raw = item.get("steps") or []
        if not isinstance(steps_raw, list):
            steps_raw = [str(steps_raw)]

        steps: list[TestStep] = [
            TestStep(action="instruction", value=str(step)) for step in steps_raw
        ]

        tags: list[str] = []
        category = item.get("category")
        priority = item.get("priority")
        if isinstance(category, str):
            tags.append(category)
        if isinstance(priority, str):
            tags.append(priority)

        metadata: dict[str, Any] = {}
        for key in ("test_id", "expected_result", "category", "priority"):
            if key in item:
                metadata[key] = item[key]

        tc = TestCaseCreate(
            name=name,
            url=url,
            description=description,
            steps=steps,
            tags=tags,
            metadata=metadata,
        )
        test_case_creates.append(tc)

    repo = TestCaseRepository(project_name=project.name)
    created = await repo.create_many(test_case_creates, project_id=project_id)
    return created

