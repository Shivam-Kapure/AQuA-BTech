from __future__ import annotations

import hashlib
import json
from typing import Any

from app.models.api_spec import ApiSpecRecord
from app.services.openapi_parser import parse_openapi_document


def build_api_spec_record(
    document: str | dict[str, Any], *, owner_id: str, project_name: str | None = None, source: str = "inline"
) -> ApiSpecRecord:
    parsed = parse_openapi_document(document)
    canonical = document if isinstance(document, str) else json.dumps(document, sort_keys=True, separators=(",", ":"))
    checksum = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return ApiSpecRecord(**parsed.model_dump(), owner_id=owner_id, project_name=project_name, source=source, checksum=checksum)
