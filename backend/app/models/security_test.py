from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SecurityTestType(str, Enum):
    security_headers = "security_headers"
    cookie_security = "cookie_security"
    input_validation = "input_validation"
    authentication_configuration = "authentication_configuration"
    information_disclosure = "information_disclosure"


class SecurityTestCaseCreate(BaseModel):
    test_id: str = Field(..., description="Unique identifier (e.g., SEC001)")
    title: str = Field(..., description="Descriptive name")
    category: str = Field(..., description="Category of the security test")
    target: str = Field(..., description="Target URL, endpoint, or element")
    method: str = Field(default="", description="HTTP method or action method")
    parameter: str = Field(default="", description="Target parameter or field if applicable")
    test_type: SecurityTestType = Field(..., description="Type of the security test")
    expected_secure_behavior: str = Field(..., description="What the secure behavior should be")
    severity: str = Field(..., description="Severity (e.g., high, medium, low)")
    
    # Internal routing properties
    url: str = Field(..., description="The URL the test is associated with")


class SecurityTestCaseInDB(SecurityTestCaseCreate):
    id: str = Field(alias="_id", description="MongoDB ObjectId as string")
    project_id: str | None = None
    status: str = Field(default="draft", description="PASS | FAIL | WARNING | draft")
    failure_reason: str | None = None
    finding: str | None = None
    evidence: str | None = None
    recommendation: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
