from __future__ import annotations

from app.services.playwright_runner import _build_child_env


def test_generated_script_environment_excludes_application_secrets(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_SECRET_KEY", "must-not-leak")
    monkeypatch.setenv("GROQ_API_KEY", "must-not-leak")
    monkeypatch.setenv("PATH", "/usr/bin")

    env = _build_child_env(
        artifact_dir="playwright_artifacts/run-1",
        runtime_inputs={"TEST_EMAIL": "user@example.com", "ARTIFACT_DIR": "override"},
        route_jwt="header.payload.signature",
    )

    assert env["PATH"] == "/usr/bin"
    assert env["TEST_EMAIL"] == "user@example.com"
    assert env["ARTIFACT_DIR"] == "playwright_artifacts/run-1"
    assert env["AQUA_ROUTE_JWT"] == "header.payload.signature"
    assert "AUTH_SECRET_KEY" not in env
    assert "GROQ_API_KEY" not in env
