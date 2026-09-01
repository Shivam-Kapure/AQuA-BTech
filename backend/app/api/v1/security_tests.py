from fastapi import APIRouter
from pydantic import BaseModel

from app.models.security_test import SecurityTestCaseInDB
from app.services.security_generation_service import generate_security_tests_for_url
from app.db.repositories.project_repo import ProjectRepository
from app.db.repositories.security_test_repo import SecurityTestCaseRepository
from fastapi import HTTPException

router = APIRouter()


class GenerateSecurityTestsRequest(BaseModel):
    url: str
    project_name: str


@router.post("/generate", response_model=list[SecurityTestCaseInDB])
async def generate_security_tests(payload: GenerateSecurityTestsRequest):
    """
    Generate security tests for a given webpage using the LLM and
    store them in the database.
    """
    created = await generate_security_tests_for_url(
        url=payload.url,
        project_name=payload.project_name,
    )
    return created

@router.get("/{project_name}", response_model=list[SecurityTestCaseInDB])
async def get_security_tests_for_project(project_name: str):
    """
    List all generated security test cases for a project.
    """
    project_repo = ProjectRepository()
    project = await project_repo.get_or_create_by_name(project_name)
    if not project or not project.id:
        raise HTTPException(status_code=404, detail="Project not found")

    test_case_repo = SecurityTestCaseRepository(project_name=project.name)
    return await test_case_repo.list(project_id=project.id)

from app.services.security_run_service import run_security_test

@router.post("/{project_name}/{test_id}/execute")
async def execute_security_test(project_name: str, test_id: str):
    """
    Execute a single security test case.
    """
    result = await run_security_test(project_name=project_name, test_id=test_id)

    if result.get("error") == "project_not_found":
        raise HTTPException(status_code=404, detail="Project not found")
    if result.get("error") == "test_not_found":
        raise HTTPException(status_code=404, detail="Security test case not found")

    return result

from app.services.zap_scanner import run_zap_scan

@router.post("/zap-scan/{project_name}")
async def trigger_zap_scan(project_name: str):
    """
    Run OWASP ZAP baseline scan against the project's target URL.
    Returns structured security findings.
    """
    try:
        findings = await run_zap_scan(project_name)
        return {"message": "ZAP scan completed successfully", "findings": findings}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
