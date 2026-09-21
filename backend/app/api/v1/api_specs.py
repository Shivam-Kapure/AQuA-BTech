from __future__ import annotations

import json
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import AuthenticatedUser, get_current_user
from app.models.api_spec import ApiRunRecord, ApiSpec, ApiWorkflowStep
from app.services.openapi_parser import parse_openapi_document
from app.services.openapi_import import build_api_spec_record
from app.db.repositories.api_spec_repo import ApiSpecRepository
from app.db.repositories.api_run_repo import ApiRunRepository
from app.core.url_security import validate_target_url
from app.config import settings
from app.services.api_executor import execute_api_test
from app.services.api_workflow import execute_api_workflow
from app.services.postman_import import parse_postman_collection
from app.services.api_case_generation import generate_api_test_cases
from app.services.api_security_scan import scan_api_security
from app.models.api_spec import ApiTestCase

router = APIRouter()


class ApiSpecImportRequest(BaseModel):
    document: str | dict[str, Any] | None = None
    source_url: str | None = None
    project_name: str | None = None


class PostmanImportRequest(BaseModel):
    collection: dict[str, Any]


class ApiCaseGenerationRequest(BaseModel):
    spec: ApiSpec
    count: int = 10


class ApiSecurityScanRequest(BaseModel):
    spec: ApiSpec
    active: bool = False


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
    result = await execute_api_test(payload)
    run = await ApiRunRepository().create(ApiRunRecord(
        owner_id=_current_user.id,
        project_name=payload.project_name,
        test_name=payload.name,
        result=result,
    ))
    return run.model_dump(mode="json")


@router.post("/execute-workflow")
async def execute_api_workflow_endpoint(
    steps: list[ApiWorkflowStep],
    _current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Run an ordered setup/dependent-request workflow."""
    return await execute_api_workflow(steps)


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


@router.post("/import-postman", response_model=list[ApiTestCase])
async def import_postman_collection(
    payload: PostmanImportRequest,
    _current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[ApiTestCase]:
    try:
        return parse_postman_collection(payload.collection)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/generate-tests", response_model=list[ApiTestCase])
async def generate_api_cases(
    payload: ApiCaseGenerationRequest,
    _current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[ApiTestCase]:
    try:
        return await generate_api_test_cases(payload.spec, count=payload.count)
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/security-scan")
async def scan_api_spec_security(
    payload: ApiSecurityScanRequest,
    _current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    try:
        return await scan_api_security(payload.spec, active=payload.active)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/runs")
async def list_api_runs(
    project_name: str | None = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    runs = await ApiRunRepository().list(owner_id=current_user.id, project_name=project_name)
    return [run.model_dump(mode="json") for run in runs]


@router.get("/runs/{run_id}")
async def get_api_run(run_id: str, current_user: AuthenticatedUser = Depends(get_current_user)) -> dict[str, Any]:
    run = await ApiRunRepository().get(run_id, owner_id=current_user.id)
    if run is None:
        raise HTTPException(status_code=404, detail="API run not found")
    return run.model_dump(mode="json")
