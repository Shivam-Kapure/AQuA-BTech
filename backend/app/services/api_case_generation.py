from __future__ import annotations

import json

from app.core.llm import get_llm_client
from app.models.api_spec import ApiSpec, ApiTestCase


async def generate_api_test_cases(spec: ApiSpec, *, count: int = 10) -> list[ApiTestCase]:
    count = min(max(count, 1), 50)
    operations = [operation.model_dump() for operation in spec.operations]
    prompt = (
        "Generate JSON only: an array of API test cases. Each object must contain "
        "name, method, url, headers, query, body, and assertions. Use only the "
        f"following normalized operations and generate at most {count} cases:\n"
        f"{json.dumps(operations, separators=(',', ':'))}"
    )
    response = await get_llm_client().chat(
        [{"role": "system", "content": "You generate schema-valid API test cases."}, {"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    raw = response.text.strip()
    if "```" in raw:
        raw = raw.split("```", 2)[1].removeprefix("json").strip()
    parsed = json.loads(raw)
    if isinstance(parsed, dict):
        parsed = parsed.get("tests") or parsed.get("test_cases")
    if not isinstance(parsed, list):
        raise ValueError("LLM response must contain an array of API test cases")
    allowed = {(operation.method, operation.path) for operation in spec.operations}
    cases: list[ApiTestCase] = []
    for item in parsed[:count]:
        case = ApiTestCase.model_validate(item)
        path = case.url.split("?", 1)[0]
        if (case.method.upper(), path) not in allowed:
            raise ValueError(f"Generated case does not match an imported operation: {case.method} {path}")
        cases.append(case)
    return cases
