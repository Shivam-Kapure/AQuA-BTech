from fastapi import APIRouter

router = APIRouter()


@router.post("/")
async def execute_test():
    return {
        "message": "Test execution started"
    }