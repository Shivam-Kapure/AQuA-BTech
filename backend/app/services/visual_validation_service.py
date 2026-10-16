from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.config import settings
from app.core.browser.dom_parser import visible_text
from app.core.llm.groq_client import get_groq_client
from app.core.llm.openai_compat_client import OpenAICompatClient
from app.core.llm.prompt_context import app_context_block


def _extract_json(text: str) -> dict[str, Any]:
    t = (text or "").strip()
    if not t:
        return {}
    try:
        return json.loads(t)
    except Exception:
        pass

    s = t.find("{")
    e = t.rfind("}")
    if s >= 0 and e > s:
        try:
            return json.loads(t[s : e + 1])
        except Exception:
            return {}
    return {}


async def validate_test_outcome_from_screenshot(
    *,
    dom_after_path: str | None,
    stdout_text: str | None,
    stderr_text: str | None,
    test_name: str,
    description: str,
    expected_result: str,
    steps: list[Any],
    app_context: str | None = None,
) -> dict[str, str]:
    """
    Ask the LLM to classify pass/fail from text snapshot plus test context.
    Returns: {"status": "passed"|"failed", "failure_reason": "..."}
    """
    dom_text = ""
    if dom_after_path:
        p = Path(dom_after_path)
        if p.exists():
            dom_text = visible_text(p.read_text(encoding="utf-8", errors="ignore"))[:7000]

    steps_text = "\n".join(
        f"{i+1}. {getattr(s, 'value', None) or getattr(s, 'action', None) or s}"
        for i, s in enumerate(steps or [])
    )

    system_prompt = (
        "You are a strict QA validator. "
        "Given DOM text snapshot, runner logs, and test context, decide if the test passed or failed. "
        "Do not assume navigation is required for errors; inline validation on the same page is valid. "
        "Return ONLY JSON: "
        '{"status":"passed|failed","failure_reason":"string (empty if passed)"}'
    )

    user_text = (
        f"Test name: {test_name}\n"
        f"Description: {description or ''}\n"
        f"Expected result: {expected_result or ''}\n"
        f"Steps:\n{steps_text}\n"
        f"{app_context_block(app_context)}\n"
        f"DOM snapshot text (possibly truncated):\n{dom_text or '[not available]'}\n\n"
        f"Runner stdout:\n{(stdout_text or '')[:2000]}\n\n"
        f"Runner stderr:\n{(stderr_text or '')[:2000]}\n\n"
        "Classify strictly from the provided text evidence and context. "
        "If uncertain, choose failed and explain why."
    )

    model = settings.AGENT_LLM_MODEL or settings.LLM_MODEL
    if (settings.LLM_PROVIDER or "").lower() == "groq":
        client = get_groq_client()
    else:
        base_url = (settings.AGENT_LMSTUDIO_URL or settings.LMSTUDIO_URL).rstrip("/")
        client = OpenAICompatClient(base_url=base_url, api_key="lm-studio")

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]

    result = await client.chat(
        messages,  # type: ignore[arg-type]
        model=model,
        temperature=0.0,
        # Reasoning models (e.g. Groq's gpt-oss) spend output tokens on hidden
        # reasoning before the JSON verdict, so leave generous headroom.
        max_tokens=2048,
    )
    payload = _extract_json(result.text)
    status = str(payload.get("status") or "").lower()
    reason = str(payload.get("failure_reason") or "").strip()

    if status not in ("passed", "failed"):
        return {
            "status": "failed",
            "failure_reason": "LLM validation returned an invalid verdict format.",
        }

    if status == "passed":
        return {"status": "passed", "failure_reason": ""}
    return {"status": "failed", "failure_reason": reason or "Visual validation marked test as failed."}
