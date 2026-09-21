from __future__ import annotations

from typing import Any

import httpx

from app.models.api_spec import ApiWorkflowStep
from app.services.api_executor import _json_path, execute_api_test


async def execute_api_workflow(
    steps: list[ApiWorkflowStep], *, client: httpx.AsyncClient | None = None
) -> dict[str, Any]:
    variables: dict[str, str] = {}
    results: list[dict[str, Any]] = []
    for step in steps:
        test_case = step.test_case.model_copy(update={"variables": {**step.test_case.variables, **variables}})
        result = await execute_api_test(test_case, client=client)
        results.append({"name": step.name, "result": result})
        if not result.get("passed", False):
            return {"passed": False, "stopped_at": step.name, "steps": results}
        for variable, path in step.extract.items():
            value = _json_path(result.get("body"), path)
            if value is not None:
                variables[variable] = str(value)
    return {"passed": True, "steps": results, "variables": variables}
