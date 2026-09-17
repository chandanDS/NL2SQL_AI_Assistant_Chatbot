from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from backend.core.config import get_settings
from backend.main import app
from backend.schemas.intent import TokenUsage


@pytest.fixture(autouse=True)
def stub_semantic_insights(monkeypatch):
    async def _stub(client, payload, fallback):
        return fallback, TokenUsage(), True

    monkeypatch.setattr("backend.api.semantic.generate_rich_insights", _stub)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def branch_token(client: TestClient) -> str:
    response = client.post(
        "/auth/login",
        data={"username": "bankuser001", "password": "bankuser001"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_dynamic_average_ticket_size_by_product(client: TestClient, branch_token: str):
    response = client.post(
        "/semantic/query",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={"plan": {
            "module": "ADVANCES", "operation": "ratio", "measure": "outstanding_amount",
            "secondary_measure": "account_count", "aggregation": "sum", "as_percentage": False,
            "group_by": ["product"], "period_start": "2026-09-01", "period_end": "2026-09-01",
            "products": [], "organization_unit_id": None, "sort_descending": True, "limit": 20,
            "interpretation": "Average advance ticket size by product for September 2026",
        }},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["read_only"] is True
    assert body["unit"] == "INR_PER_ACCOUNTS"
    assert body["row_count"] == 6
    assert all(Decimal(row["value"]) > 0 for row in body["rows"])
    assert all(round(row["value"], 2) == row["value"] for row in body["rows"])
    assert "organization_unit_id" in body["generated_sql"]


def test_dynamic_average_ticket_size_returns_a_human_answer(client: TestClient, branch_token: str):
    response = client.post(
        "/semantic/query",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={"plan": {
            "module": "ADVANCES", "operation": "ratio", "measure": "outstanding_amount",
            "secondary_measure": "account_count", "aggregation": "sum", "as_percentage": False,
            "group_by": [], "period_start": "2026-09-01", "period_end": "2026-09-01",
            "products": ["HOME_LOAN"], "organization_unit_id": None, "sort_descending": True, "limit": 20,
            "interpretation": "Average home-loan ticket size for September 2026",
        }},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["row_count"] == 1
    assert "₹" in body["insights"][0]
    assert "per account" in body["insights"][0]


def test_dynamic_measure_outside_allowlist_is_rejected(client: TestClient, branch_token: str):
    response = client.post(
        "/semantic/query",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={"plan": {
            "module": "ADVANCES", "operation": "aggregate", "measure": "customer_pan",
            "secondary_measure": None, "aggregation": "sum", "as_percentage": False,
            "group_by": [], "period_start": "2026-09-01", "period_end": "2026-09-01",
            "products": [], "organization_unit_id": None, "sort_descending": True, "limit": 20,
            "interpretation": "Unsafe unsupported measure",
        }},
    )
    assert response.status_code == 422
