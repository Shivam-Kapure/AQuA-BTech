from __future__ import annotations

import pytest

from app.models.api_spec import ApiSpec
from app.services import api_case_generation


class FakeResponse:
    text = '[{"name":"get pets","method":"GET","url":"/pets","assertions":[]}]'


class FakeClient:
    async def chat(self, *_args, **_kwargs):
        return FakeResponse()


@pytest.mark.asyncio
async def test_generated_cases_are_validated_against_operations(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_case_generation, "get_llm_client", lambda: FakeClient())
    spec = ApiSpec(title="Pets", version="1", openapi_version="3.0.3", operations=[{"operation_id": "listPets", "method": "GET", "path": "/pets"}])

    cases = await api_case_generation.generate_api_test_cases(spec)

    assert cases[0].method == "GET"
    assert cases[0].decision_score == 50
    assert cases[0].decision_score_factors["priority"] == 20


@pytest.mark.asyncio
async def test_generated_cases_reject_unknown_operations(monkeypatch: pytest.MonkeyPatch) -> None:
    class InvalidClient:
        async def chat(self, *_args, **_kwargs):
            return type("Response", (), {"text": '[{"name":"bad","method":"DELETE","url":"/missing","assertions":[]}]'})()

    monkeypatch.setattr(api_case_generation, "get_llm_client", lambda: InvalidClient())
    spec = ApiSpec(title="Pets", version="1", openapi_version="3.0.3", operations=[{"operation_id": "listPets", "method": "GET", "path": "/pets"}])

    with pytest.raises(ValueError, match="does not match"):
        await api_case_generation.generate_api_test_cases(spec)


@pytest.mark.asyncio
async def test_generated_cases_are_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    text = (
        '{"tests": ['
        '{"name":"health","method":"get","url":"/health","assertions":["status == 200"]},'
        '{"name":"like","method":"POST","url":"/posts/abc123/like","assertions":[{"type":"status_code","expected":"404 Not Found"}]},'
        '{"name":"bad","method":"GET","url":"/nope","assertions":[]}'
        "]}"
    )
    monkeypatch.setattr(api_case_generation, "get_llm_client", lambda: type("C", (), {"chat": lambda *_a, **_k: _async(text)})())
    spec = ApiSpec(
        title="Demo", version="1", openapi_version="3.0.3", base_urls=["http://api.test"],
        operations=[
            {"operation_id": "health", "method": "GET", "path": "/health"},
            {"operation_id": "like", "method": "POST", "path": "/posts/{id}/like", "auth_schemes": ["bearerAuth"]},
        ],
    )

    cases = await api_case_generation.generate_api_test_cases(spec)

    assert [c.url for c in cases] == ["http://api.test/health", "http://api.test/posts/abc123/like"]
    assert cases[0].assertions[0].kind == "status" and cases[0].assertions[0].expected == 200
    # Auth-required operation called without a token must expect 401.
    assert [(a.kind, a.expected) for a in cases[1].assertions] == [("status", 401)]


async def _async(text: str):
    return type("Response", (), {"text": text})()
