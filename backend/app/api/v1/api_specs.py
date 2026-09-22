from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import AuthenticatedUser, get_current_user
from app.models.api_spec import ApiFindingRecord, ApiRunRecord, ApiSpec, ApiSpecRecord, ApiWorkflowStep
from app.services.openapi_parser import parse_openapi_document
from app.services.openapi_import import build_api_spec_record
from app.db.repositories.api_spec_repo import ApiSpecRepository
from app.db.repositories.api_run_repo import ApiRunRepository
from app.db.repositories.api_finding_repo import ApiFindingRepository
from app.core.url_security import validate_redirect_target, validate_target_url
from app.config import settings
from app.services.api_executor import execute_api_test
from app.services.api_workflow import execute_api_workflow
from app.services.postman_import import parse_postman_collection
from app.services.api_case_generation import generate_api_test_cases
from app.services.api_security_scan import scan_api_security
from app.models.api_spec import ApiTestCase
from app.models.test_run import RunStatus
from app.services.job_queue import job_queue

router = APIRouter()


class ApiSpecImportRequest(BaseModel):
    document: str | dict[str, Any] | None = None
    source_url: str | None = None
    project_name: str | None = None

    model_config = {"json_schema_extra": {"examples": [{"document": {"openapi": "3.0.3", "info": {"title": "Example", "version": "1.0.0"}, "paths": {}}}]}}


class PostmanImportRequest(BaseModel):
    collection: dict[str, Any]

    model_config = {"json_schema_extra": {"examples": [{"collection": {"info": {"schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"}, "item": []}}]}}


class ApiCaseGenerationRequest(BaseModel):
    spec: ApiSpec
    count: int = 10

    model_config = {"json_schema_extra": {"examples": [{"spec": {"title": "Example", "version": "1.0.0", "openapi_version": "3.0.3", "operations": []}, "count": 5}]}}


class ApiSecurityScanRequest(BaseModel):
    spec: ApiSpec
    active: bool = False
    project_name: str | None = None


class ApiFindingRemediationRequest(BaseModel):
    remediation_status: str
    remediation_note: str | None = None


@router.post("/parse", response_model=ApiSpec)
async def parse_api_spec(
    payload: ApiSpecImportRequest,
    _current_user: AuthenticatedUser = Depends(get_current_user),
) -> ApiSpec:
    try:
        return parse_openapi_document(payload.document)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/execute", response_model=ApiRunRecord)
async def execute_api_spec_test(
    payload: ApiTestCase,
    _current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Execute one explicitly supplied API test case without persisting secrets."""
    result = await execute_api_test(payload)
    passed = bool(result.get("passed"))
    run = await ApiRunRepository().create(ApiRunRecord(
        owner_id=_current_user.id,
        project_name=payload.project_name,
        test_name=payload.name,
        result=result,
        status=RunStatus.passed if passed else RunStatus.failed,
        duration_ms=result.get("response_time_ms"),
        runner_version="api-httpx-v1",
        generation_mode="deterministic",
        evidence=result,
        failure_details=None if passed else {"reason": "One or more API assertions failed", "assertions": result.get("assertions", [])},
        correlation_id=str(uuid.uuid4()),
    ))
    return run.model_dump(mode="json")


@router.post("/execute-async")
async def execute_api_spec_test_async(
    payload: ApiTestCase,
    timeout_seconds: float = 30.0,
    max_retries: int = 0,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Queue an API execution and return its durable queued run immediately."""
    correlation_id = str(uuid.uuid4())
    repository = ApiRunRepository()
    queued = await repository.create(ApiRunRecord(
        owner_id=current_user.id,
        project_name=payload.project_name,
        test_name=payload.name,
        result={},
        status=RunStatus.queued,
        runner_version="api-httpx-v1",
        generation_mode="deterministic",
        correlation_id=correlation_id,
    ))

    async def factory() -> dict[str, Any]:
        await repository.update_by_correlation(
            correlation_id,
            owner_id=current_user.id,
            fields={"status": RunStatus.running.value, "started_at": datetime.utcnow()},
        )
        try:
            result = await execute_api_test(payload)
        except Exception as exc:
            await repository.update_by_correlation(
                correlation_id,
                owner_id=current_user.id,
                fields={
                    "status": RunStatus.failed.value,
                    "failure_details": {"reason": str(exc)},
                    "completed_at": datetime.utcnow(),
                },
            )
            raise
        passed = bool(result.get("passed"))
        await repository.update_by_correlation(
            correlation_id,
            owner_id=current_user.id,
            fields={
                "status": (RunStatus.passed if passed else RunStatus.failed).value,
                "result": result,
                "evidence": result,
                "duration_ms": result.get("response_time_ms"),
                "failure_details": None if passed else {"reason": "One or more API assertions failed", "assertions": result.get("assertions", [])},
                "completed_at": datetime.utcnow(),
            },
        )
        return result

    job = await job_queue.submit(
        factory,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        job_id=correlation_id,
        owner_id=current_user.id,
    )
    return {"job_id": job.id, "run": queued.model_dump(mode="json")}


@router.get("/jobs/{job_id}")
async def get_api_job(job_id: str, current_user: AuthenticatedUser = Depends(get_current_user)) -> dict[str, Any]:
    job = job_queue.get(job_id)
    if job is None or job.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="API job not found")
    run = await ApiRunRepository().get_by_correlation(job_id, owner_id=current_user.id)
    return {"job": job.as_dict(), "run": run.model_dump(mode="json") if run else None}


@router.post("/jobs/{job_id}/cancel")
async def cancel_api_job(job_id: str, current_user: AuthenticatedUser = Depends(get_current_user)) -> dict[str, Any]:
    job = job_queue.get(job_id)
    if job is None or job.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="API job not found")
    cancelled = await job_queue.cancel(job_id)
    await ApiRunRepository().update_by_correlation(
        job_id,
        owner_id=current_user.id,
        fields={"status": RunStatus.cancelled.value, "completed_at": datetime.utcnow()},
    )
    return {"job": cancelled.as_dict() if cancelled else None}


@router.post("/execute-workflow")
async def execute_api_workflow_endpoint(
    steps: list[ApiWorkflowStep],
    _current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Run an ordered setup/dependent-request workflow."""
    return await execute_api_workflow(steps)


@router.post("/import", response_model=ApiSpecRecord)
async def import_api_spec(
    payload: ApiSpecImportRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    document = payload.document
    source = "inline"
    if document is None and payload.source_url:
        source_url = validate_target_url(payload.source_url)
        async with httpx.AsyncClient(verify=settings.HTTP_VERIFY_TLS, follow_redirects=False, timeout=20.0) as client:
            response = await client.get(source_url)
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise HTTPException(status_code=502, detail="OpenAPI import redirect did not provide a Location header")
                redirected_url = validate_redirect_target(source_url, location)
                response = await client.get(redirected_url)
        if len(response.content) > 2 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="OpenAPI document exceeds the 2 MiB limit")
        response.raise_for_status()
        document = response.text
        source = str(response.url)
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


@router.get("/", response_model=list[ApiSpecRecord])
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
        findings = await scan_api_security(payload.spec, active=payload.active)
        records = [ApiFindingRecord(owner_id=_current_user.id, project_name=payload.project_name, operation_id=finding.get("operation_id"), category=finding["category"], status=finding["status"], severity=finding.get("severity", "medium"), finding=finding["finding"]) for finding in findings]
        await ApiFindingRepository().create_many(records)
        return findings
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/security-scan-async")
async def scan_api_spec_security_async(
    payload: ApiSecurityScanRequest,
    timeout_seconds: float = 60.0,
    max_retries: int = 0,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Queue a passive security scan; active probes remain explicitly unsupported."""
    if payload.active:
        raise HTTPException(status_code=422, detail="Active API security probes require an isolated worker policy")
    correlation_id = str(uuid.uuid4())
    repository = ApiRunRepository()
    queued = await repository.create(ApiRunRecord(
        owner_id=current_user.id,
        project_name=payload.project_name,
        test_name="API passive security scan",
        result={},
        status=RunStatus.queued,
        runner_version="api-security-v1",
        generation_mode="passive",
        correlation_id=correlation_id,
    ))

    async def factory() -> dict[str, Any]:
        await repository.update_by_correlation(
            correlation_id,
            owner_id=current_user.id,
            fields={"status": RunStatus.running.value, "started_at": datetime.utcnow()},
        )
        try:
            findings = await scan_api_security(payload.spec, active=False)
            records = [ApiFindingRecord(owner_id=current_user.id, project_name=payload.project_name, operation_id=finding.get("operation_id"), category=finding["category"], status=finding["status"], severity=finding.get("severity", "medium"), finding=finding["finding"]) for finding in findings]
            await ApiFindingRepository().create_many(records)
            result = {"passed": not findings, "status": (RunStatus.warning if findings else RunStatus.passed).value, "findings": findings}
            await repository.update_by_correlation(
                correlation_id,
                owner_id=current_user.id,
                fields={
                    "status": (RunStatus.warning if findings else RunStatus.passed).value,
                    "result": result,
                    "evidence": result,
                    "completed_at": datetime.utcnow(),
                },
            )
            return result
        except Exception as exc:
            await repository.update_by_correlation(
                correlation_id,
                owner_id=current_user.id,
                fields={"status": RunStatus.failed.value, "failure_details": {"reason": str(exc)}, "completed_at": datetime.utcnow()},
            )
            raise

    job = await job_queue.submit(
        factory,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        job_id=correlation_id,
        owner_id=current_user.id,
    )
    return {"job_id": job.id, "run": queued.model_dump(mode="json")}


@router.get("/runs", response_model=list[ApiRunRecord])
async def list_api_runs(
    project_name: str | None = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    runs = await ApiRunRepository().list(owner_id=current_user.id, project_name=project_name)
    return [run.model_dump(mode="json") for run in runs]


@router.get("/runs/{run_id}", response_model=ApiRunRecord)
async def get_api_run(run_id: str, current_user: AuthenticatedUser = Depends(get_current_user)) -> dict[str, Any]:
    run = await ApiRunRepository().get(run_id, owner_id=current_user.id)
    if run is None:
        raise HTTPException(status_code=404, detail="API run not found")
    return run.model_dump(mode="json")


@router.get("/findings", response_model=list[ApiFindingRecord])
async def list_api_findings(
    project_name: str | None = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[ApiFindingRecord]:
    return await ApiFindingRepository().list(owner_id=current_user.id, project_name=project_name)


@router.patch("/findings/{finding_id}", response_model=ApiFindingRecord)
async def update_api_finding_remediation(
    finding_id: str,
    payload: ApiFindingRemediationRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ApiFindingRecord:
    if payload.remediation_status not in {"open", "accepted", "fixed"}:
        raise HTTPException(status_code=422, detail="Invalid remediation status")
    finding = await ApiFindingRepository().update_remediation(
        finding_id,
        owner_id=current_user.id,
        remediation_status=payload.remediation_status,
        remediation_note=payload.remediation_note,
    )
    if finding is None:
        raise HTTPException(status_code=404, detail="API finding not found")
    return finding
