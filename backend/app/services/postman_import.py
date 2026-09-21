from __future__ import annotations

from typing import Any

from app.models.api_spec import ApiTestCase


def parse_postman_collection(document: dict[str, Any]) -> list[ApiTestCase]:
    info = document.get("info")
    if not isinstance(info, dict) or not str(info.get("schema", "")).endswith("collection.json"):
        raise ValueError("Only Postman Collection v2.x documents are supported")

    cases: list[ApiTestCase] = []

    def walk(items: list[dict[str, Any]]) -> None:
        for item in items:
            if isinstance(item.get("item"), list):
                walk(item["item"])
                continue
            request = item.get("request")
            if not isinstance(request, dict):
                continue
            url = request.get("url")
            if isinstance(url, dict):
                url = url.get("raw")
            if not isinstance(url, str) or not url:
                continue
            headers = {str(header.get("key")): str(header.get("value", "")) for header in request.get("header", []) if isinstance(header, dict) and header.get("key")}
            body = request.get("body")
            body_value = body.get("raw") if isinstance(body, dict) else None
            cases.append(ApiTestCase(
                name=str(item.get("name") or f"{request.get('method', 'GET')} {url}"),
                method=str(request.get("method", "GET")),
                url=url,
                headers=headers,
                body=body_value,
            ))

    walk(document.get("item") or [])
    return cases
