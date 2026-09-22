from bson import ObjectId
from fastapi.testclient import TestClient
import app.main as main_module
import app.api.v1.auth as auth_module
from app.main import app
from app.core.auth import create_access_token

client = TestClient(app)

def test_liveness_endpoint():
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_missing_database(monkeypatch):
    monkeypatch.setattr(main_module, "get_database", lambda: None)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["detail"] == "MongoDB is not connected"


def test_protected_api_route_requires_authentication():
    response = client.post("/api/v1/api-specs/parse", json={"document": {}})

    assert response.status_code == 401


def test_authenticated_openapi_parse_contract():
    token = create_access_token(user_id="user-1", username="tester")
    response = client.post(
        "/api/v1/api-specs/parse",
        headers={"Authorization": f"Bearer {token}"},
        json={"document": {"openapi": "3.0.3", "info": {"title": "Demo", "version": "1"}, "paths": {}}},
    )

    assert response.status_code == 200
    assert response.json()["openapi_version"] == "3.0.3"


def test_active_security_scan_contract_fails_closed():
    token = create_access_token(user_id="user-1", username="tester")
    response = client.post(
        "/api/v1/api-specs/security-scan-async",
        headers={"Authorization": f"Bearer {token}"},
        json={"active": True, "spec": {"title": "Demo", "version": "1", "openapi_version": "3.0.3"}},
    )

    assert response.status_code == 422
    assert "isolated worker" in response.json()["detail"]


def test_auth_register_and_login_contract(monkeypatch):
    class FakeUsers:
        def __init__(self):
            self.document = None

        async def find_one(self, query):
            if self.document and self.document["username"] == query["username"]:
                return self.document
            return None

        async def insert_one(self, document):
            self.document = {**document, "_id": ObjectId()}
            return type("InsertResult", (), {"inserted_id": self.document["_id"]})()

    class FakeDatabase:
        def __init__(self, users):
            self.users = users

        def __getitem__(self, name):
            assert name == "users"
            return self.users

    users = FakeUsers()
    monkeypatch.setattr(auth_module, "get_database", lambda: FakeDatabase(users))
    register = client.post("/api/v1/auth/register", json={"username": "tester", "password": "password"})
    login = client.post("/api/v1/auth/login", json={"username": "tester", "password": "password"})

    assert register.status_code == 200
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
