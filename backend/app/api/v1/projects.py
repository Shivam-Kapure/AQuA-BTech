from fastapi import APIRouter

from app.db.repositories.project_repo import ProjectRepository
from app.models.project import ProjectCreate, ProjectInDB

router = APIRouter()


@router.get("/", response_model=list[ProjectInDB])
async def get_projects():
    repo = ProjectRepository()
    return await repo.list()


@router.post("/", response_model=ProjectInDB)
async def create_project(payload: ProjectCreate):
    repo = ProjectRepository()
    return await repo.create_one(payload)