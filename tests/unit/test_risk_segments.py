from datetime import date
from decimal import Decimal

import pytest

from backend.ml.service import _serialize, risk_review_reason, risk_segment
from backend.models.ml_leads import RiskMismatchLead, RiskReviewLead


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


def test_risk_review_reasons_explain_the_matching_threshold():
    assert "2.02x" in risk_review_reason(81, "TIER_1")
    assert "Super Red (at least 2x)" in risk_review_reason(81, "TIER_1")
    assert "1.80x" in risk_review_reason(81, "TIER_2")
    assert "Red (at least 1.5x)" in risk_review_reason(81, "TIER_2")
    assert "does not exceed the 80% threshold" in risk_review_reason(80, "TIER_1")
    assert "below the 1.5x rule" in risk_review_reason(81, "TIER_4")


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
    assert "Super Red (at least 2x)" in result["review_status"]
    assert result["risk_segment"] == "Super Red"
    assert "risk_team_tag" not in result
    assert "reason_code" not in result


def test_risk_tag_review_does_not_expose_reason_code_or_team_tag():
    record = RiskMismatchLead(
        customer_ref="CUST000000002",
        customer_name="Demo Customer",
        as_of_date=date(2026, 9, 16),
        business_unit="TIER_2",
        interest_rate_pct=Decimal("12.00"),
        model_risk_score=19,
        model_risk_band="LOW",
        risk_team_tag="BAD",
        review_status="RISK_REVIEW_REQUIRED",
        reason_code="TAG_MODEL_MISMATCH",
    )
    result = _serialize(record, "Mumbai Branch 01")
    assert "risk_team_tag" not in result
    assert "reason_code" not in result
