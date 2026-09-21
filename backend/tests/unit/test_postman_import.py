from app.services.postman_import import parse_postman_collection


def test_parse_postman_collection_v2() -> None:
    cases = parse_postman_collection({
        "info": {"schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
        "item": [{"name": "health", "request": {"method": "GET", "url": {"raw": "https://api.example.test/health"}}}],
    })

    assert len(cases) == 1
    assert cases[0].name == "health"
    assert cases[0].method == "GET"
