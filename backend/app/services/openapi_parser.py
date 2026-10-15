from __future__ import annotations

import json
from typing import Any

import yaml

from app.models.api_spec import ApiOperation, ApiSpec


MAX_OPENAPI_DOCUMENT_BYTES = 2 * 1024 * 1024
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


def _load_document(document: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(document, str):
        if len(document.encode("utf-8")) > MAX_OPENAPI_DOCUMENT_BYTES:
            raise ValueError("OpenAPI document exceeds the 2 MiB limit")
        try:
            parsed = json.loads(document)
        except json.JSONDecodeError:
            parsed = yaml.safe_load(document)
    elif isinstance(document, dict):
        parsed = document
    else:
        raise ValueError("OpenAPI document must be JSON/YAML text or an object")
    if not isinstance(parsed, dict):
        raise ValueError("OpenAPI document must contain an object at its root")
    version = parsed.get("openapi")
    if not isinstance(version, str) or not version.startswith("3."):
        raise ValueError("Only OpenAPI 3.x documents are supported")
    return parsed


def _resolve_local_refs(value: Any, root: dict[str, Any], seen: frozenset[str] = frozenset()) -> Any:
    """Resolve local JSON Pointer references without fetching remote documents."""
    if isinstance(value, list):
        return [_resolve_local_refs(item, root, seen) for item in value]
    if not isinstance(value, dict):
        return value
    reference = value.get("$ref")
    if isinstance(reference, str) and reference.startswith("#/") and reference not in seen:
        target: Any = root
        try:
            for segment in reference[2:].split("/"):
                target = target[segment.replace("~1", "/").replace("~0", "~")]
        except (KeyError, TypeError):
            return value
        resolved = _resolve_local_refs(target, root, seen | {reference})
        siblings = {key: item for key, item in value.items() if key != "$ref"}
        if isinstance(resolved, dict):
            return {**resolved, **_resolve_local_refs(siblings, root, seen)}
        return resolved
    return {key: _resolve_local_refs(item, root, seen) for key, item in value.items()}


def parse_openapi_document(document: str | dict[str, Any]) -> ApiSpec:
    raw = _load_document(document)
    info = raw.get("info") or {}
    if not isinstance(info, dict) or not info.get("title") or not info.get("version"):
        raise ValueError("OpenAPI info.title and info.version are required")

    security_schemes = ((raw.get("components") or {}).get("securitySchemes") or {})
    global_security = raw.get("security") or []
    operations: list[ApiOperation] = []
    for path, path_item in (raw.get("paths") or {}).items():
        if not isinstance(path, str) or not isinstance(path_item, dict):
            continue
        path_parameters = path_item.get("parameters") or []
        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            parameters = _resolve_local_refs([*path_parameters, *(operation.get("parameters") or [])], raw)
            request_schema = ((operation.get("requestBody") or {}).get("content") or {})
            request_schema = next(iter(request_schema.values()), {}).get("schema") if request_schema else None
            response_schema = None
            responses = operation.get("responses") or {}
            for response in responses.values():
                content = response.get("content") if isinstance(response, dict) else None
                if content:
                    response_schema = next(iter(content.values()), {}).get("schema")
                    if response_schema:
                        break
            security = operation.get("security", global_security)
            auth_names = [name for requirement in security for name in requirement if name in security_schemes]
            operation_id = operation.get("operationId") or f"{method.lower()}_{path.strip('/').replace('/', '_').replace('{', '').replace('}', '') or 'root'}"
            operations.append(ApiOperation(
                operation_id=operation_id,
                method=method.upper(),
                path=path,
                summary=operation.get("summary") or operation.get("description"),
                tags=operation.get("tags") or [],
                parameters=parameters,
                request_schema=request_schema,
                response_schema=response_schema,
                auth_schemes=auth_names,
            ))

    servers = raw.get("servers") or []
    base_urls = [server["url"] for server in servers if isinstance(server, dict) and isinstance(server.get("url"), str)]
    return ApiSpec(
        title=str(info["title"]),
        version=str(info["version"]),
        openapi_version=str(raw["openapi"]),
        base_urls=base_urls,
        operations=operations,
    )
