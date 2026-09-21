from app.services.openapi_import import build_api_spec_record


def test_import_record_has_stable_checksum() -> None:
    document = {"openapi": "3.0.3", "info": {"title": "Demo", "version": "1"}, "paths": {}}
    first = build_api_spec_record(document, owner_id="u1")
    second = build_api_spec_record(document, owner_id="u1")

    assert first.checksum == second.checksum
    assert first.owner_id == "u1"
