import pytest
from fastapi.testclient import TestClient

from backend.core.config import get_settings
from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_branch_user_cannot_request_bank_wide_analytics(client: TestClient):
    login = client.post(
        "/auth/login",
        data={
            "username": "bankuser001",
            "password": "bankuser001",
        },
    )
    assert login.status_code == 200, login.text

    response = client.post(
        "/intent/interpret",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        json={"message": "SHOW me total savings deposit in terms of amount for bank as a whole"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Bank-wide analytics requires an HO user. Your query was not executed."
