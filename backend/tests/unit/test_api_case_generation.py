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


@pytest.mark.asyncio
async def test_generated_cases_reject_unknown_operations(monkeypatch: pytest.MonkeyPatch) -> None:
    class InvalidClient:
        async def chat(self, *_args, **_kwargs):
            return type("Response", (), {"text": '[{"name":"bad","method":"DELETE","url":"/missing","assertions":[]}]'})()

    monkeypatch.setattr(api_case_generation, "get_llm_client", lambda: InvalidClient())
    spec = ApiSpec(title="Pets", version="1", openapi_version="3.0.3", operations=[{"operation_id": "listPets", "method": "GET", "path": "/pets"}])

    with pytest.raises(ValueError, match="does not match"):
        await api_case_generation.generate_api_test_cases(spec)
