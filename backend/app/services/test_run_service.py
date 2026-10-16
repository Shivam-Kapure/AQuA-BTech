"""
Run a single test case by generating a Playwright script from its steps,
executing it, and setting status to passed/failed based on actual run result.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from app.config import settings
from app.db.repositories.project_repo import ProjectRepository
from app.db.repositories.test_case_repo import TestCaseRepository
from app.services.playwright_generator import generate_playwright_script
from app.services.playwright_runner import run_playwright_script
from app.services.visual_validation_service import validate_test_outcome_from_screenshot


_ASSERTION_PATTERN = re.compile(r"\bexpect\(|\bassert\b|\.to_(?:be|have)_")


# Failures that point at a bug in the generated script rather than in the app.
_SCRIPT_BUG_MARKERS = (
    "strict mode violation", "TypeError", "AttributeError", "NameError", "SyntaxError",
    "IndentationError", "unexpected keyword argument", "is not a valid selector", "Unexpected token",
    "ModuleNotFoundError", "ImportError", "KeyError",
)
_LLM_MODES = {"llm", "llm_resume", "cached"}


# locator("word") with a bare word is a CSS tag selector; if the word is not an HTML tag,
# the script mistook a value (e.g. a username) for a selector.
_BARE_LOCATOR = re.compile(r'waiting for locator\("([A-Za-z][\w-]*)"\)')
_HTML_TAGS = {
    "a", "abbr", "article", "aside", "b", "body", "button", "canvas", "dd", "details", "dialog", "div", "dl", "dt",
    "em", "fieldset", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "html", "i", "iframe",
    "img", "input", "label", "legend", "li", "main", "nav", "ol", "option", "p", "pre", "section", "select", "small",
    "span", "strong", "summary", "table", "tbody", "td", "template", "textarea", "th", "thead", "time", "tr", "ul", "video",
}


def _is_script_bug(reason: str | None) -> bool:
    if not reason:
        return False
    if any(marker in reason for marker in _SCRIPT_BUG_MARKERS):
        return True
    match = _BARE_LOCATOR.search(reason)
    return bool(match) and match.group(1).lower() not in _HTML_TAGS


async def _execute_and_evaluate(
    script: str,
    *,
    artifact_subdir: str,
    route_jwt: str | None,
    inputs: dict[str, str] | None,
    tc: Any,
    expected: str,
    app_context: str | None,
) -> tuple[str, str | None, list[dict[str, str]] | None, Any]:
    """Run a script and classify it: (status, failure_reason, required_inputs, artifacts)."""
    result = await run_playwright_script(
        script,
        timeout_seconds=settings.PLAYWRIGHT_RUN_TIMEOUT_S,
        artifact_subdir=artifact_subdir,
        runtime_inputs=inputs or {},
        route_jwt=route_jwt,
    )
    artifacts = result.get("artifacts") or {}
    required_inputs = artifacts.get("required_inputs") if isinstance(artifacts, dict) else None
    missing_arg_inputs = _missing_positional_inputs(result)
    requested = {
        str(item.get("name")) for item in (required_inputs or missing_arg_inputs or []) if isinstance(item, dict)
    }
    already_given = {key for key, value in (inputs or {}).items() if value}
    if requested and requested <= already_given:
        # Asking again for inputs the user already supplied would loop forever.
        return (
            "failed",
            "The generated script asked again for inputs that were already provided "
            f"({', '.join(sorted(requested))}). Run the test again to regenerate the script.",
            None,
            artifacts,
        )
    # Waiting protocol: script exits with code 2 and/or emits required_inputs.
    if result.get("exit_code") == 2 or required_inputs or missing_arg_inputs:
        return "waiting", None, required_inputs or missing_arg_inputs, artifacts
    status, reason = await _decide_outcome(
        result, artifacts, script, tc=tc, expected=expected, app_context=app_context
    )
    return status, reason, None, artifacts


async def _repair_script(
    script: str, reason: str, *, tc: Any, expected: str, app_context: str | None, input_keys: list[str] | None
) -> str | None:
    """Ask the LLM once to fix a script that failed because of its own bug."""
    try:
        repaired = await generate_playwright_script(
            test_name=tc.name,
            url=tc.url,
            description=tc.description or "",
            steps=tc.steps,
            expected_result=expected,
            runtime_input_keys=input_keys,
            app_context=app_context,
            repair=(script, reason),
        )
    except Exception as exc:
        logger.warning(f"Script repair failed for {tc.name!r}: {exc}")
        return None
    return repaired if repaired and repaired.strip() else None


def _generation_failure_reason(exc: Exception) -> str:
    text = str(exc)
    if "429" in text or "rate limit" in text.lower():
        return "Could not write the test script: the LLM provider's rate limit was reached. Run the test again in a minute."
    return f"Could not write the test script: {text[:300]}"


def _clean_error(result: dict[str, Any], artifacts: Any) -> str:
    """Best human-readable failure message from a Playwright run."""
    if isinstance(artifacts, dict) and artifacts.get("error"):
        return str(artifacts["error"])
    error_text = result.get("stderr", "") or ""
    if error_text:
        lines = error_text.strip().split("\n")
        for i, line in enumerate(reversed(lines)):
            if "Error:" in line or "Exception:" in line:
                return "\n".join(lines[-i - 1 :]).strip()
        return "\n".join(lines[-2:])
    return result.get("failure_reason") or "Playwright run failed"


async def _decide_outcome(
    result: dict[str, Any],
    artifacts: Any,
    script: str,
    *,
    tc: Any,
    expected: str,
    app_context: str | None,
) -> tuple[str, str | None]:
    """
    Final pass/fail for a finished (non-waiting) run.

    The Playwright run is authoritative: a failed script fails the test with its
    real error, and a passing script that made assertions passes. The LLM verdict
    is only consulted when the script passed without asserting anything, since
    then the run alone does not show whether the expected result happened.
    """
    if not result["success"]:
        return "failed", _clean_error(result, artifacts)
    if _ASSERTION_PATTERN.search(script or ""):
        return "passed", None

    artifacts_dir = artifacts.get("artifact_dir") if isinstance(artifacts, dict) else None
    dom_after = Path(str(artifacts_dir)) / "dom_after.html" if artifacts_dir else None
    if not dom_after or not dom_after.exists():
        return "passed", None
    verdict = await validate_test_outcome_from_screenshot(
        dom_after_path=str(dom_after),
        stdout_text=result.get("stdout"),
        stderr_text=result.get("stderr"),
        test_name=tc.name,
        description=tc.description or "",
        expected_result=expected,
        steps=tc.steps,
        app_context=app_context,
    )
    return verdict["status"], verdict.get("failure_reason") or None


def _safe_filename(s: str) -> str:
    return re.sub(r"[^\w\-.]", "_", s)[:80]


def _missing_positional_inputs(result: dict[str, Any]) -> list[dict[str, str]]:
    """
    Parse Python TypeError style errors:
    "... missing 1 required positional argument: 'foo'"
    and return required_inputs for action-needed flow.
    """
    text = "\n".join(
        [
            str(result.get("failure_reason") or ""),
            str(result.get("stderr") or ""),
            str(result.get("stdout") or ""),
        ]
    )
    names = re.findall(r"required positional argument[s]?:\s*'([^']+)'", text, flags=re.IGNORECASE)
    uniq: list[str] = []
    for n in names:
        if n and n not in uniq:
            uniq.append(n)
    return [
        {
            "name": f"TEST_ARG_{name.upper()}",
            "hint": f"Provide value for missing required argument '{name}'",
        }
        for name in uniq
    ]


async def run_single_test(
    project_name: str, test_id: str, *, owner_id: str | None = None, route_jwt: str | None = None
) -> dict[str, Any]:
    """
    Run one test case: fetch it, generate a Playwright script from its steps,
    execute the script, then set status to passed/failed based on execution result
    (no LLM decision — do and verify).
    test_id can be metadata.test_id (e.g. TC001).
    """
    project_repo = ProjectRepository()
    test_repo = TestCaseRepository(project_name=project_name)

    project = await project_repo.get_by_name(project_name, owner_id=owner_id)
    if not project or not project.id:
        return {"error": "project_not_found", "status": None, "failure_reason": None}

    tc = await test_repo.get_by_project_and_test_id(
        project_id=project.id,
        test_id=test_id,
    )
    if not tc or not tc.id:
        return {"error": "test_not_found", "status": None, "failure_reason": None}

    await test_repo.update_status(tc.id, status="waiting", failure_reason=None)

    expected = (tc.metadata or {}).get("expected_result") or "Success"

    # Reuse the script from the last passing run when there is one (fast, no LLM call);
    # otherwise generate with the LLM, falling back to the deterministic builder.
    cached_script = await test_repo.get_cached_script(tc.id)
    try:
        if cached_script:
            script, generation_mode = cached_script, "cached"
        else:
            script = await generate_playwright_script(
                test_name=tc.name,
                url=tc.url,
                description=tc.description or "",
                steps=tc.steps,
                expected_result=expected,
                app_context=project.description,
            )
            generation_mode = "llm"
    except Exception as exc:
        # A template script cannot follow natural-language steps and would report a
        # misleading failure, so say plainly that the script could not be written.
        reason = _generation_failure_reason(exc)
        logger.warning(f"Script generation failed for {tc.name!r}: {exc}")
        await test_repo.update_status(tc.id, status="failed", failure_reason=reason)
        return {
            "status": "failed",
            "failure_reason": reason,
            "test_id": tc.id,
            "test_name": tc.name,
            "script_path": None,
            "generation_mode": None,
            "dom": None,
        }

    if not script or not script.strip():
        await test_repo.update_status(
            tc.id,
            status="failed",
            failure_reason="LLM did not produce a valid Playwright script.",
        )
        return {
            "status": "failed",
            "failure_reason": "LLM did not produce a valid Playwright script.",
            "test_id": tc.id,
            "test_name": tc.name,
            "script_path": None,
            "generation_mode": None,
            "dom": None,
        }

    # Optionally save script to a directory so you can open and inspect it
    script_path: str | None = None
    if settings.PLAYWRIGHT_SCRIPT_OUTPUT_DIR:
        out_dir = Path(settings.PLAYWRIGHT_SCRIPT_OUTPUT_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_id = _safe_filename(tc.id or test_id)
        fname = f"{_safe_filename(project_name)}_{safe_id}_{ts}.py"
        path = out_dir / fname
        path.write_text(script, encoding="utf-8")
        script_path = str(path.resolve())

    # Execute script; pass/fail from actual run. A script that fails because of its
    # own bug (strict-mode locator, bad API call, ...) is regenerated once with the
    # error as feedback before the result is reported.
    artifact_subdir = f"{_safe_filename(project_name)}_{_safe_filename(tc.id or test_id)}"
    run_kwargs = dict(artifact_subdir=artifact_subdir, route_jwt=route_jwt, inputs=None, tc=tc, expected=expected, app_context=project.description)
    status, failure_reason, required_inputs, artifacts = await _execute_and_evaluate(script, **run_kwargs)
    if status == "failed" and generation_mode in _LLM_MODES and _is_script_bug(failure_reason):
        repaired = await _repair_script(
            script, failure_reason or "", tc=tc, expected=expected, app_context=project.description, input_keys=None
        )
        if repaired:
            script, generation_mode = repaired, "llm_repaired"
            if script_path:
                Path(script_path).write_text(script, encoding="utf-8")
            status, failure_reason, required_inputs, artifacts = await _execute_and_evaluate(script, **run_kwargs)

    await test_repo.update_status(tc.id, status=status, failure_reason=failure_reason)
    if status == "passed" and generation_mode in {"llm", "llm_repaired"}:
        await test_repo.set_cached_script(tc.id, script)
    elif status != "passed" and cached_script:
        # The cached script no longer passes (app changed?); regenerate next run.
        await test_repo.set_cached_script(tc.id, None)

    dom_info = None
    if isinstance(artifacts, dict) and ("dom_hash_before" in artifacts or "dom_hash_after" in artifacts):
        dom_info = {
            "dom_hash_before": artifacts.get("dom_hash_before"),
            "dom_hash_after": artifacts.get("dom_hash_after"),
            "dom_changed": artifacts.get("dom_changed"),
            "artifact_dir": artifacts.get("artifact_dir"),
        }

    return {
        "status": status,
        "failure_reason": failure_reason,
        "test_id": tc.id,
        "test_name": tc.name,
        "script_path": script_path,
        "generation_mode": generation_mode,
        "dom": dom_info,
        "required_inputs": required_inputs,
    }


async def resume_single_test(
    project_name: str,
    test_id: str,
    *,
    inputs: dict[str, str] | None = None,
    owner_id: str | None = None,
    route_jwt: str | None = None,
) -> dict[str, Any]:
    """
    Resume a waiting test with user-provided runtime inputs.
    Inputs are forwarded as environment variables to the test script process.
    """
    project_repo = ProjectRepository()
    test_repo = TestCaseRepository(project_name=project_name)

    project = await project_repo.get_by_name(project_name, owner_id=owner_id)
    if not project or not project.id:
        return {"error": "project_not_found", "status": None, "failure_reason": None}

    tc = await test_repo.get_by_project_and_test_id(
        project_id=project.id,
        test_id=test_id,
    )
    if not tc or not tc.id:
        return {"error": "test_not_found", "status": None, "failure_reason": None}

    await test_repo.update_status(tc.id, status="waiting", failure_reason=None)

    expected = (tc.metadata or {}).get("expected_result") or "Success"
    try:
        script = await generate_playwright_script(
            test_name=tc.name,
            url=tc.url,
            description=tc.description or "",
            steps=tc.steps,
            expected_result=expected,
            runtime_input_keys=list((inputs or {}).keys()),
            app_context=project.description,
        )
        generation_mode = "llm_resume"
    except Exception as exc:
        reason = _generation_failure_reason(exc)
        logger.warning(f"Script generation failed for {tc.name!r}: {exc}")
        await test_repo.update_status(tc.id, status="failed", failure_reason=reason)
        return {
            "status": "failed",
            "failure_reason": reason,
            "test_id": tc.id,
            "test_name": tc.name,
            "script_path": None,
            "generation_mode": None,
            "dom": None,
            "required_inputs": None,
        }

    artifact_subdir = f"{_safe_filename(project_name)}_{_safe_filename(tc.id or test_id)}"
    run_kwargs = dict(artifact_subdir=artifact_subdir, route_jwt=route_jwt, inputs=inputs, tc=tc, expected=expected, app_context=project.description)
    status, failure_reason, required_inputs, _artifacts = await _execute_and_evaluate(script, **run_kwargs)
    if status == "failed" and generation_mode in _LLM_MODES and _is_script_bug(failure_reason):
        repaired = await _repair_script(
            script, failure_reason or "", tc=tc, expected=expected, app_context=project.description,
            input_keys=list((inputs or {}).keys()),
        )
        if repaired:
            script, generation_mode = repaired, "llm_resume_repaired"
            status, failure_reason, required_inputs, _artifacts = await _execute_and_evaluate(script, **run_kwargs)

    await test_repo.update_status(tc.id, status=status, failure_reason=failure_reason)

    return {
        "status": status,
        "failure_reason": failure_reason,
        "test_id": tc.id,
        "test_name": tc.name,
        "script_path": None,
        "generation_mode": generation_mode,
        "dom": None,
        "required_inputs": required_inputs,
    }
