from fastapi import APIRouter, HTTPException

from app.db.repositories.project_repo import ProjectRepository
from app.db.repositories.test_case_repo import TestCaseRepository
from app.models.test_case import TestCaseInDB

router = APIRouter()


@router.get("/{project_name}", response_model=list[TestCaseInDB])
async def get_test_cases_for_project(project_name: str):
    project_repo = ProjectRepository()
    project = await project_repo.get_or_create_by_name(project_name)

    if not project or not project.id:
        raise HTTPException(status_code=404, detail="Project not found")

    test_case_repo = TestCaseRepository(project_name=project.name)
    return await test_case_repo.list(project_id=project.id)