import pytest
from fastapi.testclient import TestClient

from backend.core.config import get_settings
from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as value:
        yield value


def token(client, username):
    response = client.post("/auth/login", data={"username": username, "password": username})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_history_and_usage_are_available_to_authenticated_user(client):
    headers = {"Authorization": f"Bearer {token(client, 'bankuser001')}"}
    sessions = client.get("/history/sessions", headers=headers)
    usage = client.get("/usage/summary", headers=headers)
    assert sessions.status_code == 200
    assert all(set(item) >= {"id", "preview", "message_count", "total_tokens"} for item in sessions.json()["sessions"])
    assert usage.status_code == 200
    assert set(usage.json()) == {"input_tokens", "output_tokens", "total_tokens", "calls", "daily"}


def test_audit_is_ho_only(client):
    branch = {"Authorization": f"Bearer {token(client, 'bankuser001')}"}
    ho = {"Authorization": f"Bearer {token(client, 'houser001')}"}
    assert client.get("/audit/events", headers=branch).status_code == 403
    response = client.get("/audit/events", headers=ho)
    assert response.status_code == 200
    assert any(item["event_type"] == "LOGIN" for item in response.json()["events"])
