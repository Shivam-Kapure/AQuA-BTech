from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.config import settings
from app.core.llm.openai_compat_client import OpenAICompatClient


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
) -> dict[str, str]:
    """
    Ask the LLM to classify pass/fail from text snapshot plus test context.
    Returns: {"status": "passed"|"failed", "failure_reason": "..."}
    """
    dom_text = ""
    if dom_after_path:
        p = Path(dom_after_path)
        if p.exists():
            raw = p.read_text(encoding="utf-8", errors="ignore")
            no_script = re.sub(r"<script[\s\S]*?</script>", " ", raw, flags=re.IGNORECASE)
            no_style = re.sub(r"<style[\s\S]*?</style>", " ", no_script, flags=re.IGNORECASE)
            stripped = re.sub(r"<[^>]+>", " ", no_style)
            dom_text = re.sub(r"\s+", " ", stripped).strip()
            dom_text = dom_text[:7000]

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
        f"Steps:\n{steps_text}\n\n"
        f"DOM snapshot text (possibly truncated):\n{dom_text or '[not available]'}\n\n"
        f"Runner stdout:\n{(stdout_text or '')[:2000]}\n\n"
        f"Runner stderr:\n{(stderr_text or '')[:2000]}\n\n"
        "Classify strictly from the provided text evidence and context. "
        "If uncertain, choose failed and explain why."
    )

    base_url = (settings.AGENT_LMSTUDIO_URL or settings.LMSTUDIO_URL).rstrip("/")
    model = settings.AGENT_LLM_MODEL or settings.LLM_MODEL
    client = OpenAICompatClient(base_url=base_url, api_key="lm-studio")

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]

    result = await client.chat(
        messages,  # type: ignore[arg-type]
        model=model,
        temperature=0.0,
        max_tokens=300,
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
