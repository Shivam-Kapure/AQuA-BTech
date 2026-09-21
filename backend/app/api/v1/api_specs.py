from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import AuthenticatedUser, get_current_user
from app.models.api_spec import ApiSpec
from app.services.openapi_parser import parse_openapi_document
from app.services.api_executor import execute_api_test
from app.models.api_spec import ApiTestCase

router = APIRouter()


class ApiSpecImportRequest(BaseModel):
    document: str | dict[str, Any]


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
