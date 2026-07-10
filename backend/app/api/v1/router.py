from fastapi import APIRouter

from app.api.v1 import agent
from app.api.v1 import test_generation
from app.api.v1 import test_execution
from app.api.v1 import test_run
from app.api.v1 import test_cases
from app.api.v1 import projects
from app.api.v1 import llm
from app.api.v1 import auth

router = APIRouter()

router.include_router(
    test_generation.router,
    prefix="/generate",
    tags=["Test Generation"],
)

router.include_router(
    test_execution.router,
    prefix="/execute",
    tags=["Test Execution"],
)

router.include_router(
    test_cases.router,
    prefix="/test-cases",
    tags=["Test Cases"],
)

router.include_router(
    projects.router,
    prefix="/projects",
    tags=["Projects"],
)

router.include_router(
    llm.router,
    prefix="/llm",
    tags=["LLM"],
)

router.include_router(
    agent.router,
    prefix="/agent",
    tags=["Agent"],
)

router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Auth"],
)

# Run a single test: /api/v1/{project_name}/{test_id}
# (kept at root by design as requested)
router.include_router(
    test_run.router,
    prefix="",
    tags=["Test Run"],
)