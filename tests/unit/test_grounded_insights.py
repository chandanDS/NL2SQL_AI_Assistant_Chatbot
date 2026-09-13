from datetime import date
from decimal import Decimal

from backend.insights.service import deterministic_insights, grounded_follow_ups, permitted_codes
from backend.schemas.analytics import AnalyticsQueryRequest, AnalyticsQueryResponse, ComparisonType
from backend.schemas.insights import InsightCode


def result(**updates) -> AnalyticsQueryResponse:
    values = {
        "kpi_code": "DEPOSIT_ACCOUNT_COUNT", "module": "DEPOSITS", "unit": "ACCOUNTS",
        "period_start": date(2026, 3, 1), "period_end": date(2026, 3, 1),
        "effective_organization_id": 5, "organization_count": 1, "products": ["CA", "SA"],
        "actual_value": Decimal("12000"), "target_value": Decimal("13000"),
        "gap_to_target": Decimal("-1000"), "shortfall_to_target": Decimal("1000"),
        "achievement_percent": Decimal("92.31"), "comparison": ComparisonType.YOY,
        "comparison_value": Decimal("10500"), "growth_percent": Decimal("14.29"),
        "row_count": 2, "formula_version": 1,
    }
    values.update(updates)
    return AnalyticsQueryResponse(**values)


def test_narrative_numbers_come_from_query_result():
    insights = deterministic_insights(result())
    combined = " ".join(insights)
    assert "12,000" in combined
    assert "1,000" in combined
    assert "92.31%" in combined
    assert "14.29%" in combined


def test_unavailable_evidence_cannot_be_selected():
    available = permitted_codes(result(target_value=None, comparison_value=None, comparison=ComparisonType.NONE))
    assert available == [InsightCode.ACTUAL_SUMMARY]


def test_empty_result_has_explicit_message_and_no_followups():
    empty = result(actual_value=Decimal(0), target_value=None, comparison_value=None, row_count=0)
    request = AnalyticsQueryRequest(
        kpi_code=empty.kpi_code, period_start=empty.period_start, period_end=empty.period_end
    )
    assert deterministic_insights(empty)[0].startswith("No records were found")
    assert grounded_follow_ups(request, empty) == []


def test_followups_are_complete_validated_query_plans():
    request = AnalyticsQueryRequest(
        kpi_code="DEPOSIT_ACCOUNT_COUNT", period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 1), products=["CA", "SA"], comparison=ComparisonType.NONE,
    )
    followups = grounded_follow_ups(request, result(comparison=ComparisonType.NONE, comparison_value=None))
    assert {item.analytics_request.comparison for item in followups[:2]} == {ComparisonType.YOY, ComparisonType.QOQ}
    assert all(item.analytics_request.period_start == date(2026, 3, 1) for item in followups)
