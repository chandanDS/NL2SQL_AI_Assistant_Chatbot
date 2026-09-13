from datetime import date

from backend.llm.intent_service import context_from_intent, token_breakdown, try_fast_intent, validate_and_complete
from backend.schemas.analytics import ComparisonType
from backend.schemas.intent import BankingModule, ExtractedIntent, IntentStatus, TokenUsage
from backend.rbac.scope import requests_bank_wide_scope
from backend.schemas.semantic import SemanticQueryPlan


def make_intent(**overrides) -> ExtractedIntent:
    values = {
        "status": IntentStatus.READY,
        "module": BankingModule.DEPOSITS,
        "kpi_code": "DEPOSIT_ACCOUNT_COUNT",
        "period_start": date(2026, 3, 1),
        "period_end": date(2026, 3, 1),
        "products": ["CA", "SA"],
        "comparison": ComparisonType.YOY,
        "organization_unit_id": None,
        "confidence": 0.95,
        "missing_fields": [],
        "clarification_question": None,
        "interpretation": "CASA accounts for March 2026 versus March 2025",
    }
    values.update(overrides)
    return ExtractedIntent(**values)


def test_complete_intent_produces_validated_analytics_request():
    intent, request = validate_and_complete(make_intent())
    assert intent.status == IntentStatus.READY
    assert request is not None
    assert request.kpi_code == "DEPOSIT_ACCOUNT_COUNT"
    assert request.products == ["CA", "SA"]


def test_missing_period_defaults_to_current_month():
    intent, request = validate_and_complete(
        make_intent(period_start=None, period_end=None, missing_fields=["period_start"])
    )
    assert intent.status == IntentStatus.READY
    assert intent.missing_fields == []
    assert request is not None
    assert request.period_start == date.today().replace(day=1)
    assert request.period_end == date.today().replace(day=1)


def test_broad_module_question_uses_primary_kpi():
    intent, request = validate_and_complete(
        make_intent(status=IntentStatus.NEEDS_CLARIFICATION, module=BankingModule.ADVANCES,
                    kpi_code=None, period_start=None, period_end=None, products=[],
                    confidence=0.55, missing_fields=["kpi_code", "period"])
    )
    assert intent.status == IntentStatus.READY
    assert request is not None
    assert request.kpi_code == "ADVANCE_OUTSTANDING_AMOUNT"


def test_unknown_kpi_is_unsupported():
    intent, request = validate_and_complete(make_intent(kpi_code="UNAPPROVED_KPI"))
    assert intent.status == IntentStatus.UNSUPPORTED
    assert request is None


def test_structured_context_contains_resolved_fields():
    context = context_from_intent(make_intent())
    assert context["kpi_code"] == "DEPOSIT_ACCOUNT_COUNT"
    assert context["period_start"] == "2026-03-01"
    assert context["products"] == ["CA", "SA"]


def test_token_breakdown_is_additive_and_sql_uses_no_llm_tokens():
    breakdown = token_breakdown(
        TokenUsage(input_tokens=100, output_tokens=20, total_tokens=120),
        "Show advances",
        [{"role": "user", "content": "Earlier question"}],
    )
    assert breakdown.sql_generation_tokens == 0
    assert breakdown.user_input_tokens + breakdown.context_history_tokens + breakdown.routing_tokens == 120
    assert breakdown.overall_tokens == 120


def test_dynamic_token_breakdown_attributes_model_output_to_sql_planning():
    breakdown = token_breakdown(
        TokenUsage(input_tokens=100, output_tokens=20, total_tokens=120),
        "Show average loan ticket size by product",
        [{"role": "user", "content": "Earlier question"}],
        dynamic_sql_plan=True,
    )
    assert breakdown.sql_generation_tokens == 20
    assert (
        breakdown.user_input_tokens
        + breakdown.context_history_tokens
        + breakdown.routing_tokens
        + breakdown.sql_generation_tokens
        == breakdown.overall_tokens
    )


def test_valid_dynamic_plan_bypasses_fixed_kpi_catalogue():
    plan = SemanticQueryPlan(
        module="ADVANCES", operation="ratio", measure="outstanding_amount",
        secondary_measure="account_count", aggregation="sum", as_percentage=False,
        group_by=["product"], period_start=date(2026, 9, 1), period_end=date(2026, 9, 1),
        interpretation="Average advance ticket size by product",
    )
    intent, request = validate_and_complete(make_intent(kpi_code=None, dynamic_query_plan=plan))
    assert intent.status == IntentStatus.READY
    assert intent.dynamic_query_plan == plan
    assert request is None


def test_bank_wide_scope_language_is_detected():
    assert requests_bank_wide_scope("SHOW me total savings deposit for bank as a whole")
    assert requests_bank_wide_scope("Show this bank-wide")
    assert not requests_bank_wide_scope("Show deposits for my branch")


def test_clear_fixed_kpi_uses_zero_token_fast_path():
    result = try_fast_intent("Show total savings deposit amount for September 2026")
    assert result is not None
    intent, request = result
    assert intent.kpi_code == "DEPOSIT_BUSINESS_AMOUNT"
    assert request.products == ["SA"]
    assert request.period_start == date(2026, 9, 1)


def test_derived_metric_is_left_for_dynamic_llm_planner():
    assert try_fast_intent("Show average home loan ticket size for September 2026") is None
