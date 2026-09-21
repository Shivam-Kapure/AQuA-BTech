from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.models.test_case import TestCaseInDB
from app.services.test_generation_service import generate_test_cases_for_url
from app.core.auth import AuthenticatedUser, get_current_user

router = APIRouter()


class GenerateTestsRequest(BaseModel):
    url: str
    project_name: str


@router.post("/", response_model=list[TestCaseInDB])
async def generate_tests(
    payload: GenerateTestsRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Generate tests for a given webpage using the LLM and
    store them in the database.
    """

    created = await generate_test_cases_for_url(
        url=payload.url,
        project_name=payload.project_name,
        owner_id=current_user.id,
    )
    return created
