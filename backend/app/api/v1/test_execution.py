from fastapi import APIRouter, Depends

from app.core.auth import AuthenticatedUser, get_current_user

router = APIRouter()


@router.post("/")
async def execute_test(
    _current_user: AuthenticatedUser = Depends(get_current_user),
):
    return {
        "message": "Test execution started"
    }
