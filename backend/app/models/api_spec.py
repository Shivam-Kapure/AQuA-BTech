from __future__ import annotations

from typing import Any
from datetime import datetime

from pydantic import BaseModel, Field


class ApiOperation(BaseModel):
    operation_id: str
    method: str
    path: str
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    parameters: list[dict] = Field(default_factory=list)
    request_schema: dict | None = None
    response_schema: dict | None = None
    auth_schemes: list[str] = Field(default_factory=list)


class ApiSpec(BaseModel):
    title: str
    version: str
    openapi_version: str
    base_urls: list[str] = Field(default_factory=list)
    operations: list[ApiOperation] = Field(default_factory=list)


class ApiSpecRecord(ApiSpec):
    id: str | None = None
    owner_id: str
    project_name: str | None = None
    source: str = "inline"
    checksum: str
    version: int = 1
    imported_at: datetime = Field(default_factory=datetime.utcnow)


class ApiAssertion(BaseModel):
    kind: str
    expected: Any = None
    path: str | None = None


class ApiTestCase(BaseModel):
    name: str
    project_name: str | None = None
    method: str
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    query: dict[str, str] = Field(default_factory=dict)
    body: dict | list | str | None = None
    variables: dict[str, str] = Field(default_factory=dict)
    auth_context: "ApiAuthContext | None" = None
    assertions: list[ApiAssertion] = Field(default_factory=list)


class ApiAuthContext(BaseModel):
    scheme: str = "bearer"
    token: str | None = None


class ApiRunRecord(BaseModel):
    id: str | None = None
    owner_id: str
    project_name: str | None = None
    test_name: str
    result: dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ApiWorkflowStep(BaseModel):
    name: str
    test_case: ApiTestCase
    extract: dict[str, str] = Field(default_factory=dict)
