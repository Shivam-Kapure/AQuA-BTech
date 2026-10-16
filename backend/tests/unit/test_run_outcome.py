from types import SimpleNamespace

import pytest

import app.services.test_run_service as run_service
from app.services.visual_validation_service import visible_text

TC = SimpleNamespace(name="Login", description="", steps=[])


async def _decide(result, script, artifacts=None):
    return await run_service._decide_outcome(
        result, artifacts or {}, script, tc=TC, expected="Logged in", app_context=None
    )


@pytest.mark.asyncio
async def test_passing_script_with_assertions_passes_without_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_if_called(**_kwargs):
        raise AssertionError("LLM verdict must not override a passing Playwright run")

    monkeypatch.setattr(run_service, "validate_test_outcome_from_screenshot", fail_if_called)
    status, reason = await _decide({"success": True}, 'expect(page.locator("#logout")).to_be_hidden()')
    assert (status, reason) == ("passed", None)


@pytest.mark.asyncio
async def test_failing_script_fails_with_its_own_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_if_called(**_kwargs):
        raise AssertionError("LLM verdict must not override a failed Playwright run")

    monkeypatch.setattr(run_service, "validate_test_outcome_from_screenshot", fail_if_called)
    result = {"success": False, "stderr": "Traceback ...\nAssertionError: Locator expected to be visible"}
    status, reason = await _decide(result, "expect(x).to_be_visible()")
    assert status == "failed"
    assert reason == "AssertionError: Locator expected to be visible"


@pytest.mark.asyncio
async def test_passing_script_without_assertions_asks_llm(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    (tmp_path / "dom_after.html").write_text("<p>hi</p>", encoding="utf-8")

    async def verdict(**_kwargs):
        return {"status": "failed", "failure_reason": "Expected text missing"}

    monkeypatch.setattr(run_service, "validate_test_outcome_from_screenshot", verdict)
    status, reason = await _decide({"success": True}, "page.click('#login')", {"artifact_dir": str(tmp_path)})
    assert (status, reason) == ("failed", "Expected text missing")


def test_visible_text_drops_hidden_elements() -> None:
    html = (
        '<span id="session">@bob</span><button id="logout" class="link hidden">Sign out</button>'
        '<div style="display: none">secret</div><p hidden>gone</p><template><b>tpl</b></template>'
        "<button>Sign in</button>"
    )
    assert visible_text(html) == "@bob Sign in"
