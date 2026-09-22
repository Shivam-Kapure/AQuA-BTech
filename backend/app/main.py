import httpx
from fastapi import FastAPI, HTTPException, status
from contextlib import asynccontextmanager

from app.config import settings
from app.db.mongodb import connect_to_mongo, close_mongo_connection, get_database
from app.api.v1.router import router as api_router
from app.db.repositories.api_finding_repo import ApiFindingRepository
from app.db.repositories.api_run_repo import ApiRunRepository
from app.db.repositories.api_spec_repo import ApiSpecRepository
from app.db.repositories.test_run_repo import TestRunRepository
from app.db.repositories.artifact_repo import ArtifactRepository
from app.db.repositories.project_repo import ProjectRepository
from app.services.job_queue import job_queue


async def _check_llm_readiness() -> dict[str, str]:
    provider = (settings.LLM_PROVIDER or "lmstudio").lower()
    if provider == "groq":
        if not settings.GROQ_API_KEY:
            return {"status": "not_configured", "provider": provider}
        base_url = "https://api.groq.com/openai"
        headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
    elif provider == "lmstudio":
        base_url = settings.LMSTUDIO_URL
        headers = {}
    else:
        return {"status": "unsupported", "provider": provider}

    try:
        timeout = max(0.1, min(settings.LLM_READINESS_TIMEOUT_S, 5.0))
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{base_url.rstrip('/')}/v1/models", headers=headers)
        if response.is_success:
            return {"status": "ok", "provider": provider}
        return {"status": "unavailable", "provider": provider}
    except httpx.HTTPError:
        return {"status": "unavailable", "provider": provider}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    await ProjectRepository().ensure_indexes()
    await ApiSpecRepository().ensure_indexes()
    await ApiRunRepository().ensure_indexes()
    await ApiFindingRepository().ensure_indexes()
    await TestRunRepository().ensure_indexes()
    await ArtifactRepository().ensure_indexes()
    yield
    await close_mongo_connection()


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def root():
    return {"message": "Agentic Testing System Running"}


@app.get("/health/live")
def liveness():
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness():
    database = get_database()
    if database is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not connected")
    try:
        await database.command("ping")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MongoDB is not ready") from exc
    llm = await _check_llm_readiness()
    dependencies = {
        "mongodb": "ok",
        "worker": {"status": "ok", "mode": "process-local", "active_jobs": len(job_queue._jobs)},
        "llm": llm,
    }
    if settings.LLM_READINESS_REQUIRED and llm["status"] != "ok":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": "LLM is not ready", "dependencies": dependencies},
        )
    return {"status": "ok", "dependencies": dependencies}
