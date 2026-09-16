from datetime import date
from decimal import Decimal

import pytest

from backend.ml.service import _serialize, risk_segment
from backend.models.ml_leads import RiskReviewLead


@pytest.mark.parametrize(
    ("probability", "business_unit", "expected"),
    [
        (80, "TIER_1", "Risk Review"),
        (81, "TIER_1", "Super Red"),
        (90, "TIER_2", "Super Red"),
        (81, "TIER_2", "Red"),
        (82, "TIER_3", "Red"),
        (81, "TIER_4", "Risk Review"),
        (81, "UNKNOWN", "Risk Review"),
    ],
)
def test_risk_segment_thresholds(probability, business_unit, expected):
    assert risk_segment(probability, business_unit) == expected


def test_risk_scorecard_output_uses_reason_as_review_status_and_hides_internal_tags():
    record = RiskReviewLead(
        customer_ref="CUST000000001",
        customer_name="Demo Customer",
        as_of_date=date(2026, 9, 16),
        business_unit="TIER_1",
        interest_rate_pct=Decimal("12.00"),
        risk_score=81,
        risk_band="HIGH",
        risk_team_tag="HIGH_RISK",
        review_status="AVOID_PENDING_REVIEW",
        reason_code="ELEVATED_RISK_SCORE",
    )
    result = _serialize(record, "Mumbai Branch 01")
    assert result["review_status"] == "Elevated Risk Score"
    assert result["risk_segment"] == "Super Red"
    assert "risk_team_tag" not in result
    assert "reason_code" not in result
