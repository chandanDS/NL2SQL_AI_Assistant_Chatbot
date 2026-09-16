import pytest

from backend.ml.service import identify_lead_intent
from frontend.prediction_followups import prediction_followups


@pytest.mark.parametrize(
    ("organization", "expected_scope"),
    [
        ("Mumbai Branch 01", "for Mumbai branch 1"),
        ("National Head Office", "for the bank as a whole"),
        ("West Circle", "in my assigned scope"),
    ],
)
def test_followups_preserve_a_supported_scope(organization, expected_scope):
    questions = prediction_followups(organization)
    assert len(questions) == 9
    assert all(expected_scope in question for question in questions.values())
    assert {identify_lead_intent(question).use_case for question in questions.values()} == {
        "campaign", "underwriting", "risk_review", "risk_mismatch", "propensity",
    }


def test_propensity_followups_target_each_band():
    questions = prediction_followups("Mumbai Branch 01")
    for label, band in (
        ("Very-high PL propensity", "VERY_HIGH"),
        ("High PL propensity", "HIGH"),
        ("Medium PL propensity", "MEDIUM"),
        ("Low PL propensity", "LOW"),
    ):
        assert identify_lead_intent(questions[label]).filters == (("propensity_band", band),)
