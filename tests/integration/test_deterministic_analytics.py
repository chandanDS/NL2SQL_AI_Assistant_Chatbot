import pytest
from decimal import Decimal
from fastapi.testclient import TestClient

from backend.core.config import get_settings
from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def branch_token(client: TestClient) -> str:
    response = client.post(
        "/auth/login",
        data={
            "username": "bankuser0137",
            "password": get_settings().synthetic_user_password.get_secret_value(),
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.integration
@pytest.mark.parametrize(
    ("kpi", "comparison", "unit"),
    [
        ("DEPOSIT_BUSINESS_AMOUNT", "yoy", "INR"),
        ("DEPOSIT_ACCOUNT_COUNT", "qoq", "ACCOUNTS"),
        ("ADVANCE_ACCOUNT_COUNT", "none", "ACCOUNTS"),
        ("ASSET_QUALITY_RECOVERY_AMOUNT", "none", "INR"),
    ],
)
def test_approved_deterministic_queries(client, branch_token, kpi, comparison, unit):
    response = client.post(
        "/analytics/query",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={
            "kpi_code": kpi,
            "period_start": "2026-01-01",
            "period_end": "2026-03-01",
            "comparison": comparison,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert Decimal(body["actual_value"]) > 0
    assert body["row_count"] > 0
    assert body["unit"] == unit
    assert body["read_only"] is True
    assert body["generated_sql"]
    assert "SELECT" in body["generated_sql"][0]
    assert "organization_unit_id" in body["generated_sql"][0]
    if comparison != "none":
        assert Decimal(body["comparison_value"]) > 0
        assert body["growth_percent"] is not None
        assert len(body["generated_sql"]) == 2


@pytest.mark.integration
def test_unapproved_kpi_is_rejected(client, branch_token):
    response = client.post(
        "/analytics/query",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={
            "kpi_code": "DROP_TABLE_USERS",
            "period_start": "2026-01-01",
            "period_end": "2026-03-01",
        },
    )
    assert response.status_code == 422


@pytest.mark.integration
def test_invalid_product_is_rejected(client, branch_token):
    response = client.post(
        "/analytics/query",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={
            "kpi_code": "DEPOSIT_ACCOUNT_COUNT",
            "period_start": "2026-01-01",
            "period_end": "2026-03-01",
            "products": ["HL"],
        },
    )
    assert response.status_code == 422
