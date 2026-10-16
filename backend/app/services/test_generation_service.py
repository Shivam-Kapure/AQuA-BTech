from __future__ import annotations

import json
from typing import Any

from app.core.llm import get_llm_client
from app.core.llm.prompt_context import app_context_block
from app.db.repositories.project_repo import ProjectRepository
from app.db.repositories.test_case_repo import TestCaseRepository
from app.models.test_case import TestCaseCreate, TestStep, TestCaseInDB
from app.services.decision_scoring import decision_metadata

# New imports for context-aware generation
from app.core.browser.playwright_controller import fetch_page_html
from app.core.browser.dom_parser import build_dom_context_string, extract_interactive_elements, page_text_excerpt
from app.core.rag.knowledge_manager import KnowledgeManager
from loguru import logger

def _extract_json_array(raw: str) -> str:
    """Extract the JSON array from an LLM reply (handles ```json fences, etc.)."""
    if "```" in raw:
        start = raw.find("```json")
        if start == -1:
            start = raw.find("```")
            start += 3
        else:
            start += len("```json")
        end = raw.find("```", start)
        if end != -1:
            return raw[start:end].strip()
        return raw
    first = raw.find("[")
    last = raw.rfind("]")
    if first != -1 and last != -1 and last > first:
        return raw[first : last + 1]
    return raw


# Test cases per profile. Generated in batches so each LLM request stays well under
# free-tier tokens-per-minute limits (one 20-case reply would not fit in one request).
_PROFILE_TEST_COUNTS = {"quick": 5, "standard": 10, "detailed": 20}
_BATCH_SIZE = 5
_BATCH_FOCUS = [
    "a balanced mix of the most important happy paths, edge cases and negative tests",
    "edge cases and boundary values (lengths, limits, special characters, empty states)",
    "negative tests and error handling (invalid input, unauthorised actions, rejected requests)",
    "state changes across actions (sign in/out, create then verify, toggles, search and reset)",
]


PROMPT_TEMPLATE = """
You are an expert QA automation engineer. Analyze the following web application description and its visible DOM elements to generate comprehensive test cases.

Target URL: {url}
{context_block}
### Available UI Elements on the Page:
{dom_context}

### Visible page text (excerpt)
{page_text}

Treat facts stated in this text as authoritative: demo/test credentials, rules, limits and the exact
wording of messages it mentions. Use them in steps and expected results instead of guessing.

Elements marked hidden='initially' are not visible on first load; they appear only after an action (for example signing in). Do not expect them to be visible before that action.

## Your Task
Generate exactly {test_count} high‑quality test cases that would be appropriate for this page, ONLY using the elements provided above.
Focus for this batch: {focus}.
{existing_block} DO NOT guess element IDs or classes that are not listed above. Include:
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


async def _generate_batch(client: Any, prompt: str) -> list[dict[str, Any]]:
    """One LLM call returning a list of test-case dicts, with one self-correction retry."""
    messages = [
        {"role": "system", "content": "You generate high-quality JSON test cases for web applications."},
        {"role": "user", "content": prompt},
    ]
    # Models occasionally emit invalid JSON (e.g. JavaScript expressions inside
    # strings); give the model one chance to correct itself before failing.
    for attempt in range(2):
        res = await client.chat(messages, response_format={"type": "json_object"}, reasoning_effort="medium")
        raw = res.text.strip()
        try:
            parsed = json.loads(_extract_json_array(raw))
            if isinstance(parsed, dict):
                # Accept {"test_cases": [...]}-style wrappers.
                parsed = next((v for v in parsed.values() if isinstance(v, list)), [parsed])
            if not isinstance(parsed, list):
                raise ValueError("LLM response JSON must be an array of test cases")
            return [item for item in parsed if isinstance(item, dict)]
        except json.JSONDecodeError as e:
            if attempt == 1:
                raise ValueError(f"Failed to parse LLM JSON for test cases: {e}\nRaw: {raw}") from e
            logger.warning(f"LLM returned invalid JSON ({e}); asking it to correct the output")
            messages = messages + [
                {"role": "assistant", "content": raw},
                {
                    "role": "user",
                    "content": (
                        f"That output is not valid JSON ({e}). Return ONLY the corrected JSON array. "
                        "Every value must be a plain JSON string, number, boolean, array or object; "
                        "no code, concatenation or expressions."
                    ),
                },
            ]
    return []


async def generate_test_cases_for_url(
    url: str,
    *,
    project_name: str | None = None,
    owner_id: str | None = None,
    app_context: str | None = None,
    generation_profile: str | None = None,
) -> list[TestCaseInDB]:
    """
    Use the configured LLM to generate test cases for a URL
    and persist them to MongoDB. Scrapes the page first to provide context.
    """
    if not project_name:
        raise ValueError("project_name is required to generate test cases.")

    project_repo = ProjectRepository()
    project = await project_repo.get_or_create_by_name(
        project_name, url=url, owner_id=owner_id
    )
    project_id = project.id
    repo = TestCaseRepository(project_name=project.name)
    existing = await repo.list(project_id=project_id)
    if existing:
        logger.info(f"Reusing {len(existing)} existing test cases for project {project.name}")
        return existing

    # 1. Scrape the DOM and build context
    html = await fetch_page_html(url)
    elements = extract_interactive_elements(html)
    dom_context = build_dom_context_string(elements)
    page_text = page_text_excerpt(html) or "(no visible text)"
    
    # 2. Ingest into RAG for playwright generator to use later
    km = KnowledgeManager()
    if elements:
        km.ingest_elements(url, elements)

    logger.info(f"Generated DOM context length: {len(dom_context)} characters for {url}")

    client = get_llm_client()

    total = _PROFILE_TEST_COUNTS.get((generation_profile or "").lower(), 5)
    context_block = app_context_block(app_context or project.description)
    parsed: list[dict[str, Any]] = []
    for batch_index in range((total + _BATCH_SIZE - 1) // _BATCH_SIZE):
        count = min(_BATCH_SIZE, total - len(parsed))
        if count <= 0:
            break
        names = [str(item.get("test_name") or item.get("name") or "") for item in parsed]
        existing_block = (
            "Already generated (do NOT repeat or rephrase these):\n" + "\n".join(f"- {n}" for n in names if n)
            if names else ""
        )
        prompt = PROMPT_TEMPLATE.format(
            url=url,
            dom_context=dom_context,
            page_text=page_text,
            context_block=context_block,
            test_count=count,
            focus=_BATCH_FOCUS[batch_index % len(_BATCH_FOCUS)],
            existing_block=existing_block,
        )
        try:
            batch = await _generate_batch(client, prompt)
        except Exception:
            # Keep what earlier batches produced (e.g. if the daily LLM quota runs out mid-way).
            if parsed:
                logger.exception(f"Test generation batch {batch_index + 1} failed; keeping {len(parsed)} cases")
                break
            raise
        parsed.extend(batch[:count])

    # Assign our own sequential IDs: batches cannot see each other's IDs, and runs
    # look test cases up by metadata.test_id, so IDs must be unique.
    for index, item in enumerate(parsed, start=1):
        item["test_id"] = f"TC{index:03d}"

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
        metadata.update(
            decision_metadata(
                priority=priority if isinstance(priority, str) else None,
                category=category if isinstance(category, str) else None,
                steps=steps,
            )
        )

        tc = TestCaseCreate(
            name=name,
            url=url,
            description=description,
            steps=steps,
            tags=tags,
            metadata=metadata,
        )
        test_case_creates.append(tc)

    created = await repo.create_many(test_case_creates, project_id=project_id)
    return created
