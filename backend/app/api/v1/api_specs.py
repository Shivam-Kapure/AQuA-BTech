from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import AuthenticatedUser, get_current_user
from app.models.api_spec import ApiSpec
from app.services.openapi_parser import parse_openapi_document
from app.services.openapi_import import build_api_spec_record
from app.db.repositories.api_spec_repo import ApiSpecRepository
from app.core.url_security import validate_target_url
from app.config import settings
from app.services.api_executor import execute_api_test
from app.models.api_spec import ApiTestCase

router = APIRouter()


class ApiSpecImportRequest(BaseModel):
    document: str | dict[str, Any] | None = None
    source_url: str | None = None
    project_name: str | None = None


@router.post("/parse", response_model=ApiSpec)
async def parse_api_spec(
    payload: ApiSpecImportRequest,
    _current_user: AuthenticatedUser = Depends(get_current_user),
) -> ApiSpec:
    try:
        return parse_openapi_document(payload.document)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/execute")
async def execute_api_spec_test(
    payload: ApiTestCase,
    _current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Execute one explicitly supplied API test case without persisting secrets."""
    return await execute_api_test(payload)


@router.post("/import")
async def import_api_spec(
    payload: ApiSpecImportRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    document = payload.document
    source = "inline"
    if document is None and payload.source_url:
        validate_target_url(payload.source_url)
        async with httpx.AsyncClient(verify=settings.HTTP_VERIFY_TLS, follow_redirects=False, timeout=20.0) as client:
            response = await client.get(payload.source_url)
        if len(response.content) > 2 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="OpenAPI document exceeds the 2 MiB limit")
        response.raise_for_status()
        document = response.text
        source = payload.source_url
    if document is None:
        raise HTTPException(status_code=422, detail="Provide document or source_url")
    try:
        record = build_api_spec_record(document, owner_id=current_user.id, project_name=payload.project_name, source=source)
        repo = ApiSpecRepository()
        record.version = await repo.next_version(owner_id=current_user.id, project_name=payload.project_name)
        saved = await repo.create(record)
        return saved.model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/")
async def list_api_specs(
    project_name: str | None = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    records = await ApiSpecRepository().list(owner_id=current_user.id, project_name=project_name)
    return [record.model_dump(mode="json") for record in records]
