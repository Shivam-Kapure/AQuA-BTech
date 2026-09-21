from __future__ import annotations

from typing import Any
from loguru import logger

from app.db.repositories.project_repo import ProjectRepository
from app.db.repositories.security_test_repo import SecurityTestCaseRepository
from app.services.security_checkers import (
    check_security_headers,
    check_cookie_security,
    check_input_validation,
    check_information_disclosure,
    check_authentication_configuration,
)

async def run_security_test(
    project_name: str, test_id: str, *, owner_id: str | None = None
) -> dict[str, Any]:
    project_repo = ProjectRepository()
    test_repo = SecurityTestCaseRepository(project_name=project_name)

    project = await project_repo.get_by_name(project_name, owner_id=owner_id)
    if not project or not project.id:
        return {"error": "project_not_found"}

    tc = await test_repo.get_by_project_and_test_id(
        project_id=project.id,
        test_id=test_id,
    )
    if not tc or not tc.id:
        return {"error": "test_not_found"}

    # Map test_type to checker
    result = {}
    target_url = tc.target or tc.url
    
    logger.info(f"Running security test {tc.test_id} ({tc.test_type}) against {target_url}")

    if tc.test_type == "security_headers":
        result = await check_security_headers(target_url)
    elif tc.test_type == "cookie_security":
        result = await check_cookie_security(target_url)
    elif tc.test_type == "input_validation":
        result = await check_input_validation(target_url, tc.method, tc.parameter)
    elif tc.test_type == "information_disclosure":
        result = await check_information_disclosure(target_url)
    elif tc.test_type == "authentication_configuration":
        result = await check_authentication_configuration(target_url)
    else:
        result = {
            "status": "WARNING",
            "finding": f"No predefined checker available for test type: {tc.test_type}",
            "evidence": "",
            "recommendation": "Implement a checker for this test type."
        }

    # Ensure result contains all required fields
    status = result.get("status", "FAIL")
    finding = result.get("finding", "Unknown error")
    evidence = result.get("evidence", "")
    recommendation = result.get("recommendation", "")

    # Update the database
    await test_repo.update_status(
        tc.id,
        status=status,
        failure_reason=None if status == "PASS" else finding,
        finding=finding,
        evidence=evidence,
        recommendation=recommendation,
    )

    return {
        "test_id": tc.test_id,
        "status": status,
        "severity": tc.severity,
        "target": target_url,
        "finding": finding,
        "evidence": evidence,
        "recommendation": recommendation,
    }
