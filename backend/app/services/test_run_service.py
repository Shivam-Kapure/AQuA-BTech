"""
Run a single test case by generating a Playwright script from its steps,
executing it, and setting status to passed/failed based on actual run result.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import settings
from app.db.repositories.project_repo import ProjectRepository
from app.db.repositories.test_case_repo import TestCaseRepository
from app.services.playwright_generator import (
    generate_playwright_script_deterministic,
    generate_playwright_script,
)
from app.services.playwright_runner import run_playwright_script
from app.services.visual_validation_service import validate_test_outcome_from_screenshot


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


async def run_single_test(project_name: str, test_id: str) -> dict[str, Any]:
    """
    Run one test case: fetch it, generate a Playwright script from its steps,
    execute the script, then set status to passed/failed based on execution result
    (no LLM decision — do and verify).
    test_id can be metadata.test_id (e.g. TC001).
    """
    project_repo = ProjectRepository()
    test_repo = TestCaseRepository(project_name=project_name)

    project = await project_repo.get_by_name(project_name)
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

    # Generate Playwright script with LLM first (as requested).
    # Fall back to deterministic builder only if LLM generation fails.
    try:
        script = await generate_playwright_script(
            test_name=tc.name,
            url=tc.url,
            description=tc.description or "",
            steps=tc.steps,
            expected_result=expected,
        )
        generation_mode = "llm"
    except Exception:
        try:
            script = generate_playwright_script_deterministic(
                test_name=tc.name,
                url=tc.url,
                description=tc.description or "",
                steps=tc.steps,
                expected_result=expected,
            )
            generation_mode = "deterministic_fallback"
        except Exception as e:
            await test_repo.update_status(
                tc.id,
                status="failed",
                failure_reason=f"Script generation failed: {e!s}",
            )
            return {
                "status": "failed",
                "failure_reason": f"Script generation failed: {e!s}",
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

    # Execute script; pass/fail from actual run
    artifact_subdir = f"{_safe_filename(project_name)}_{_safe_filename(tc.id or test_id)}"
    result = await run_playwright_script(
        script,
        timeout_seconds=settings.PLAYWRIGHT_RUN_TIMEOUT_S,
        artifact_subdir=artifact_subdir,
    )

    artifacts = result.get("artifacts") or {}
    required_inputs = None
    if isinstance(artifacts, dict):
        required_inputs = artifacts.get("required_inputs")

    # Waiting protocol: script exits with code 2 and/or emits required_inputs.
    missing_arg_inputs = _missing_positional_inputs(result)
    if result.get("exit_code") == 2 or required_inputs or missing_arg_inputs:
        status = "waiting"
        failure_reason = None
        if missing_arg_inputs and not required_inputs:
            required_inputs = missing_arg_inputs
        await test_repo.update_status(tc.id, status=status, failure_reason=None)
    else:
        # After execution, use visual snapshot validation for final pass/fail.
        # Only waiting bypasses this.
        artifacts_dir = None
        if isinstance(artifacts, dict):
            artifacts_dir = artifacts.get("artifact_dir")
        dom_after_path = None
        if artifacts_dir:
            cand = Path(artifacts_dir) / "dom_after.html"
            if cand.exists():
                dom_after_path = str(cand)

        if not result["success"] and not dom_after_path:
            status = "failed"
            clean_error = None
            if isinstance(artifacts, dict) and artifacts.get("error"):
                clean_error = artifacts["error"]
            
            error_text = result.get("stderr", "")
            if not clean_error and error_text:
                # Pluck out the actual Exception from the bottom of the Python trace
                lines = error_text.strip().split('\n')
                for i, line in enumerate(reversed(lines)):
                    if "Error:" in line or "Exception:" in line:
                        clean_error = "\n".join(lines[-i-1:]).strip()
                        break
                if not clean_error and lines:
                    clean_error = "\n".join(lines[-2:]) # Fallback to last two lines
            
            failure_reason = clean_error or result.get("failure_reason") or "Playwright run failed"
        else:
            if not dom_after_path:
                status = "passed"
                failure_reason = (
                    "Test executed successfully, but DOM snapshot was not produced for visual validation."
                )
            else:
                verdict = await validate_test_outcome_from_screenshot(
                    dom_after_path=dom_after_path,
                    stdout_text=result.get("stdout"),
                    stderr_text=result.get("stderr"),
                    test_name=tc.name,
                    description=tc.description or "",
                    expected_result=expected,
                    steps=tc.steps,
                )
                status = verdict["status"]
                failure_reason = verdict.get("failure_reason") or None

    if status != "waiting":
        await test_repo.update_status(tc.id, status=status, failure_reason=failure_reason)

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
) -> dict[str, Any]:
    """
    Resume a waiting test with user-provided runtime inputs.
    Inputs are forwarded as environment variables to the test script process.
    """
    project_repo = ProjectRepository()
    test_repo = TestCaseRepository(project_name=project_name)

    project = await project_repo.get_by_name(project_name)
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
        )
        generation_mode = "llm_resume"
    except Exception:
        script = generate_playwright_script_deterministic(
            test_name=tc.name,
            url=tc.url,
            description=tc.description or "",
            steps=tc.steps,
            expected_result=expected,
        )
        generation_mode = "deterministic_fallback"

    artifact_subdir = f"{_safe_filename(project_name)}_{_safe_filename(tc.id or test_id)}"
    result = await run_playwright_script(
        script,
        timeout_seconds=settings.PLAYWRIGHT_RUN_TIMEOUT_S,
        artifact_subdir=artifact_subdir,
        runtime_inputs=inputs or {},
    )

    artifacts = result.get("artifacts") or {}
    required_inputs = None
    if isinstance(artifacts, dict):
        required_inputs = artifacts.get("required_inputs")

    missing_arg_inputs = _missing_positional_inputs(result)
    if result.get("exit_code") == 2 or required_inputs or missing_arg_inputs:
        status = "waiting"
        failure_reason = None
        if missing_arg_inputs and not required_inputs:
            required_inputs = missing_arg_inputs
        await test_repo.update_status(tc.id, status=status, failure_reason=None)
    else:
        artifacts = result.get("artifacts") or {}
        artifacts_dir = artifacts.get("artifact_dir") if isinstance(artifacts, dict) else None
        dom_after_path = None
        if artifacts_dir:
            cand = Path(str(artifacts_dir)) / "dom_after.html"
            if cand.exists():
                dom_after_path = str(cand)

        if not result["success"] and not dom_after_path:
            status = "failed"
            clean_error = None
            if isinstance(artifacts, dict) and artifacts.get("error"):
                clean_error = artifacts["error"]
                
            error_text = result.get("stderr", "")
            if not clean_error and error_text:
                lines = error_text.strip().split('\n')
                for i, line in enumerate(reversed(lines)):
                    if "Error:" in line or "Exception:" in line:
                        clean_error = "\n".join(lines[-i-1:]).strip()
                        break
                if not clean_error and lines:
                    clean_error = "\n".join(lines[-2:])
                    
            failure_reason = clean_error or result.get("failure_reason") or "Playwright run failed"
        else:
            if not dom_after_path:
                status = "passed"
                failure_reason = (
                    # "Test executed successfully, but DOM snapshot was not produced for visual validation."
                )
            else:
                verdict = await validate_test_outcome_from_screenshot(
                    dom_after_path=dom_after_path,
                    stdout_text=result.get("stdout"),
                    stderr_text=result.get("stderr"),
                    test_name=tc.name,
                    description=tc.description or "",
                    expected_result=expected,
                    steps=tc.steps,
                )
                status = verdict["status"]
                failure_reason = verdict.get("failure_reason") or None

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
