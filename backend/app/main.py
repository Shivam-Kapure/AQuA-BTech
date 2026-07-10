from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.config import settings
from app.db.mongodb import connect_to_mongo, close_mongo_connection
from app.api.v1.router import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
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