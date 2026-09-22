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


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
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
    return {"status": "ok", "dependencies": {"mongodb": "ok"}}
