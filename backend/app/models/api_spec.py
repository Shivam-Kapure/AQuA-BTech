from __future__ import annotations

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
