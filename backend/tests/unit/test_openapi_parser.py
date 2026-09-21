from __future__ import annotations

import pytest

from app.services.openapi_parser import parse_openapi_document


def test_parse_openapi_document_normalizes_operations() -> None:
    spec = parse_openapi_document({
        "openapi": "3.0.3",
        "info": {"title": "Pet API", "version": "1.0.0"},
        "servers": [{"url": "https://api.example.test/v1"}],
        "components": {"securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}}},
        "security": [{"bearerAuth": []}],
        "paths": {
            "/pets/{petId}": {
                "parameters": [{"name": "petId", "in": "path", "required": True}],
                "get": {
                    "operationId": "getPet",
                    "tags": ["pets"],
                    "responses": {"200": {"content": {"application/json": {"schema": {"type": "object"}}}}},
                },
            }
        },
    })

    assert spec.base_urls == ["https://api.example.test/v1"]
    assert spec.operations[0].operation_id == "getPet"
    assert spec.operations[0].auth_schemes == ["bearerAuth"]
    assert spec.operations[0].parameters[0]["in"] == "path"


def test_parse_openapi_document_rejects_unsupported_version() -> None:
    with pytest.raises(ValueError, match="Only OpenAPI 3.x"):
        parse_openapi_document({"swagger": "2.0", "info": {"title": "Old", "version": "1"}})


def test_parse_openapi_document_enforces_size_limit() -> None:
    with pytest.raises(ValueError, match="2 MiB"):
        parse_openapi_document("{" + "a" * (2 * 1024 * 1024) + "}")
