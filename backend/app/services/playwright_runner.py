"""
Execute a generated Playwright Python script in a subprocess and return pass/fail.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

# Run subprocess in thread to avoid blocking event loop
import asyncio

from app.config import settings


_SAFE_INHERITED_ENV_KEYS = (
    "PATH", "HOME", "USER", "TMPDIR", "LANG", "LC_ALL", "PLAYWRIGHT_BROWSERS_PATH"
)


def _build_child_env(
    *, artifact_dir: str, runtime_inputs: dict[str, str] | None, route_jwt: str | None
) -> dict[str, str]:
    """Build a minimal environment so generated code cannot read app secrets."""
    env = {key: os.environ[key] for key in _SAFE_INHERITED_ENV_KEYS if key in os.environ}
    env["ARTIFACT_DIR"] = artifact_dir
    if route_jwt:
        env["AQUA_ROUTE_JWT"] = route_jwt
    reserved = {"ARTIFACT_DIR", "AQUA_ROUTE_JWT"}
    for key, value in (runtime_inputs or {}).items():
        if isinstance(key, str) and key and key.isidentifier() and key not in reserved:
            env[key] = "" if value is None else str(value)
    return env


async def run_playwright_script(
    script: str,
    *,
    timeout_seconds: float = 60.0,
    artifact_subdir: str | None = None,
    runtime_inputs: dict[str, str] | None = None,
    route_jwt: str | None = None,
) -> dict[str, Any]:
    """
    Write script to a temp file, run it with `python script.py`, capture result.
    Returns:
    {
      "success": bool,
      "failure_reason": str | None,
      "exit_code": int,
      "stdout": str,
      "stderr": str,
      "artifacts": dict | None,
    }
    """
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(script)
            path = Path(f.name)
    except Exception as e:
        return {
            "success": False,
            "failure_reason": f"Failed to write script: {e}",
            "exit_code": 1,
            "stdout": "",
            "stderr": "",
            "artifacts": None,
        }

    try:
        # Provide an artifacts dir to the script via env var.
        base_dir = settings.PLAYWRIGHT_ARTIFACTS_DIR or "playwright_artifacts"
        run_id = artifact_subdir or uuid.uuid4().hex
        artifact_dir = os.path.join(base_dir, run_id)
        env = _build_child_env(
            artifact_dir=artifact_dir,
            runtime_inputs=runtime_inputs,
            route_jwt=route_jwt,
        )

        proc = await asyncio.create_subprocess_exec(
            "python",
            str(path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {
                "success": False,
                "failure_reason": (
                    f"Test run timed out after {timeout_seconds}s. "
                    "Increase PLAYWRIGHT_RUN_TIMEOUT_S if this test needs more time."
                ),
                "exit_code": 124,
                "stdout": "",
                "stderr": "",
                "artifacts": None,
            }

        stdout_text = (stdout or b"").decode("utf-8", errors="replace").strip()
        stderr_text = (stderr or b"").decode("utf-8", errors="replace").strip()

        artifacts: dict[str, Any] | None = None
        for line in stdout_text.splitlines():
            if line.startswith("__ARTIFACT_JSON__="):
                payload = line.split("=", 1)[1].strip()
                try:
                    artifacts = json.loads(payload)
                except Exception:
                    artifacts = {"raw": payload}
                break

        if proc.returncode == 0:
            return {
                "success": True,
                "failure_reason": None,
                "exit_code": 0,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "artifacts": artifacts,
            }
        return {
            "success": False,
            "failure_reason": stderr_text or f"Script exited with code {proc.returncode}",
            "exit_code": int(proc.returncode or 1),
            "stdout": stdout_text,
            "stderr": stderr_text,
            "artifacts": artifacts,
        }
    finally:
        path.unlink(missing_ok=True)
