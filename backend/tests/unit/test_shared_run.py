from app.models.api_spec import ApiRunRecord
from app.models.test_run import ArtifactMetadata, RunStatus, TestRunRecord as RunRecord
from app.db.repositories.artifact_repo import default_artifact_expiry


def test_shared_run_schema_uses_standard_status_and_evidence_fields() -> None:
    run = RunRecord(owner_id="user-1", test_name="health", status=RunStatus.passed, evidence={"status_code": 200})

    assert run.status == RunStatus.passed
    assert run.evidence["status_code"] == 200
    assert run.artifact_ids == []


def test_api_run_record_keeps_compatibility_and_durable_metadata() -> None:
    run = ApiRunRecord(owner_id="user-1", test_name="health", result={"passed": True}, status=RunStatus.passed, runner_version="api-httpx-v1")

    assert run.status == RunStatus.passed
    assert run.runner_version == "api-httpx-v1"


def test_artifact_metadata_defaults_to_redacted() -> None:
    artifact = ArtifactMetadata(owner_id="user-1", run_id="run-1", kind="response", storage_key="runs/run-1/response.json")

    assert artifact.redacted is True


def test_artifact_metadata_has_retention_expiry() -> None:
    artifact = ArtifactMetadata(owner_id="user-1", run_id="run-1", kind="response", storage_key="runs/run-1/response.json", expires_at=default_artifact_expiry())

    assert artifact.expires_at is not None
    assert artifact.expires_at > artifact.created_at
