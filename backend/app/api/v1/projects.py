from fastapi import APIRouter, Depends

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.repositories.project_repo import ProjectRepository
from app.models.project import ProjectCreate, ProjectInDB

router = APIRouter()


@router.get("/", response_model=list[ProjectInDB])
async def get_projects(current_user: AuthenticatedUser = Depends(get_current_user)):
    repo = ProjectRepository()
    return await repo.list(owner_id=current_user.id)


@router.post("/", response_model=ProjectInDB)
async def create_project(
    payload: ProjectCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    repo = ProjectRepository()
    return await repo.create_one(payload, owner_id=current_user.id)
