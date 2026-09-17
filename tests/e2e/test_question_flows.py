from datetime import date

import pytest
from fastapi.testclient import TestClient

from backend.core.config import get_settings
from backend.insights.service import deterministic_insights
from backend.main import app
from backend.schemas.analytics import ComparisonType
from backend.schemas.intent import BankingModule, ExtractedIntent, IntentStatus, TokenUsage
from backend.schemas.semantic import SemanticQueryPlan


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as value:
        yield value


@pytest.fixture(scope="module")
def headers(client):
    response = client.post("/auth/login", data={
        "username": "bankuser001",
        "password": "bankuser001",
    })
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(autouse=True)
def no_external_insight_calls(monkeypatch):
    async def fixed_stub(client, result):
        return deterministic_insights(result), TokenUsage(), True

    async def dynamic_stub(client, payload, fallback):
        return fallback, TokenUsage(), True

    monkeypatch.setattr("backend.api.insights.generate_grounded_insights", fixed_stub)
    monkeypatch.setattr("backend.api.semantic.generate_rich_insights", dynamic_stub)


@pytest.mark.e2e
@pytest.mark.parametrize("question,expected_kpi", [
    ("Show total savings deposit amount for September 2026", "DEPOSIT_BUSINESS_AMOUNT"),
    ("Show number of MSME loan accounts for September 2026", "ADVANCE_ACCOUNT_COUNT"),
    ("Show NPA recovery for September 2026", "ASSET_QUALITY_RECOVERY_AMOUNT"),
    ("Show UPI transaction count for September 2026", "DIGITAL_TRANSACTION_COUNT"),
])
def test_fixed_question_to_database_answer(client, headers, question, expected_kpi):
    intent = client.post("/intent/interpret", headers=headers, json={"message": question})
    assert intent.status_code == 200, intent.text
    interpreted = intent.json()
    assert interpreted["analytics_request"]["kpi_code"] == expected_kpi
    answer = client.post("/insights/generate", headers=headers, json={
        "analytics_request": interpreted["analytics_request"],
        "session_id": interpreted["session_id"],
    })
    assert answer.status_code == 200, answer.text
    assert answer.json()["result"]["row_count"] > 0
    assert answer.json()["insights"]


@pytest.mark.e2e
def test_dynamic_question_to_semantic_database_answer(client, headers, monkeypatch):
    plan = SemanticQueryPlan(
        module="ADVANCES", operation="ratio", measure="outstanding_amount",
        secondary_measure="account_count", aggregation="sum", products=["HL"],
        period_start=date(2026, 9, 1), period_end=date(2026, 9, 1),
        interpretation="Average home-loan ticket size for September 2026",
    )

    async def planner_stub(client, messages, structured_context):
        return ExtractedIntent(
            status=IntentStatus.READY, module=BankingModule.ADVANCES, kpi_code=None,
            period_start=date(2026, 9, 1), period_end=date(2026, 9, 1), products=["HL"],
            comparison=ComparisonType.NONE, organization_unit_id=None, confidence=0.99,
            missing_fields=[], clarification_question=None,
            interpretation=plan.interpretation, dynamic_query_plan=plan,
        ), None, TokenUsage(input_tokens=100, output_tokens=20, total_tokens=120)

    monkeypatch.setattr("backend.api.intent.extract_intent", planner_stub)
    intent = client.post("/intent/interpret", headers=headers, json={
        "message": "Show average home loan ticket size for September 2026"
    })
    assert intent.status_code == 200, intent.text
    interpreted = intent.json()
    answer = client.post("/semantic/query", headers=headers, json={
        "plan": interpreted["dynamic_query_plan"], "session_id": interpreted["session_id"]
    })
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["row_count"] == 1
    assert body["unit"] == "INR_PER_ACCOUNTS"
    assert "per account" in body["insights"][0]
