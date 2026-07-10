from __future__ import annotations

import json
from typing import Any, Literal

from app.config import settings
from app.core.llm.agent_client import get_agent_llm_client
from app.db.repositories.project_repo import ProjectRepository
from app.db.repositories.test_case_repo import TestCaseRepository
from app.services.test_generation_service import generate_test_cases_for_url


AgentAction = Literal["generate_tests", "do_nothing", "finish"]


AGENT_SYSTEM_PROMPT = """
You are a lightweight QA testing orchestrator.

You control a small set of tools:
- GENERATE_TESTS(url, project_name): generate and store test cases for the project.
- LIST_TESTS(project_name): list all stored test cases for the project (you are given a summary).

Your job is to decide the next best action to improve the project's automated test coverage.

CRITICAL:
- Always respond with a single JSON object.
- The JSON MUST have the fields: "action" and "reason".
- "action" must be one of: "generate_tests", "do_nothing", "finish".
- If "action" is "generate_tests", also include a "target_url" field.
- Keep "reason" short (1–2 sentences).
""".strip()


async def _summarize_project_state(project_name: str) -> dict[str, Any]:
    project_repo = ProjectRepository()
    test_case_repo = TestCaseRepository(project_name=project_name)

    project = await project_repo.get_or_create_by_name(project_name)
    tests = await test_case_repo.list(project_id=project.id) if project.id else []

    categories: dict[str, int] = {}
    for tc in tests:
        for tag in tc.tags:
            categories[tag] = categories.get(tag, 0) + 1

    return {
        "project": {
            "name": project.name,
            "id": project.id,
        },
        "stats": {
            "total_tests": len(tests),
            "tags_count": categories,
        },
    }


async def run_agent_once(
    *,
    project_name: str,
    url: str,
) -> dict[str, Any]:
    """
    Run a single decision step of the agent.

    For now this is one-shot: the agent inspects the current state and
    decides whether to generate tests or do nothing.
    """
    client = get_agent_llm_client()

    state = await _summarize_project_state(project_name)

    user_payload = {
        "project_name": project_name,
        "target_url": url,
        "state": state,
    }

    messages = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Here is the current project state and target URL.\n"
                "Respond with JSON as described.\n\n"
                f"{json.dumps(user_payload, ensure_ascii=False)}"
            ),
        },
    ]

    # We rely on the small Phi-4-mini model, so keep
    # temperature low and response length compact.
    res = await client.chat(
        messages,
        model=settings.AGENT_LLM_MODEL or settings.LLM_MODEL,
        temperature=0.1,
        max_tokens=256,
    )

    raw = res.text.strip()
    try:
        action_obj = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: default to generating tests once if parsing fails.
        action_obj = {
            "action": "generate_tests",
            "reason": "Failed to parse agent JSON; defaulting to generate_tests.",
            "target_url": url,
        }

    action: AgentAction = action_obj.get("action", "generate_tests")  # type: ignore[assignment]

    result: dict[str, Any] = {
        "agent_decision": action_obj,
        "effect": None,
    }

    if action == "generate_tests":
        created = await generate_test_cases_for_url(
            url=url,
            project_name=project_name,
        )
        result["effect"] = {
            "generated_test_count": len(created),
        }
    elif action in ("do_nothing", "finish"):
        result["effect"] = {"message": "No test generation performed."}

    return result

