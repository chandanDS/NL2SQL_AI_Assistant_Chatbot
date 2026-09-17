import pytest
from fastapi.testclient import TestClient

from backend.core.config import get_settings
from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as value:
        yield value


def _token(client, username):
    response = client.post("/auth/login", data={
        "username": username,
        "password": username,
    })
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.security
def test_demo_login_uses_username_and_rejects_previous_shared_password(client):
    username = "houser001"
    shared_password = get_settings().synthetic_user_password.get_secret_value()
    if shared_password and shared_password != username:
        old_login = client.post(
            "/auth/login",
            data={"username": username, "password": shared_password},
        )
        assert old_login.status_code == 401

    current_login = client.post(
        "/auth/login",
        data={"username": username, "password": username},
    )
    assert current_login.status_code == 200


@pytest.mark.security
def test_legacy_four_digit_username_is_not_accepted(client):
    response = client.post(
        "/auth/login",
        data={"username": "bankuser0002", "password": "bankuser0002"},
    )
    assert response.status_code == 401


@pytest.fixture(scope="module")
def access(client):
    ho = _token(client, "houser001")
    branch = _token(client, "bankuser001")
    scope = client.get("/auth/scope", headers={"Authorization": f"Bearer {ho}"}).json()
    ro_id = next(item["id"] for item in scope["organizations"] if item["code"] == "RO001")
    return branch, ro_id


@pytest.mark.security
def test_branch_cannot_query_parent_scope_through_analytics_api(client, access):
    branch, ro_id = access
    response = client.post("/analytics/query", headers={"Authorization": f"Bearer {branch}"}, json={
        "kpi_code": "DEPOSIT_BUSINESS_AMOUNT", "period_start": "2026-09-01",
        "period_end": "2026-09-01", "organization_unit_id": ro_id,
    })
    assert response.status_code == 403


@pytest.mark.security
def test_branch_cannot_query_parent_scope_through_semantic_api(client, access):
    branch, ro_id = access
    response = client.post("/semantic/query", headers={"Authorization": f"Bearer {branch}"}, json={"plan": {
        "module": "DEPOSITS", "operation": "aggregate", "measure": "business_amount",
        "aggregation": "sum", "group_by": [], "period_start": "2026-09-01",
        "period_end": "2026-09-01", "products": ["SA"], "organization_unit_id": ro_id,
        "interpretation": "Attempted parent-scope query",
    }})
    assert response.status_code == 403


@pytest.mark.security
@pytest.mark.parametrize("token", ["forged.token.value", "", "null"])
def test_forged_or_missing_tokens_are_rejected(client, token):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    assert client.get("/auth/me", headers=headers).status_code == 401
