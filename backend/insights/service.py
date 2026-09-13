import json
from decimal import Decimal

from openai import AsyncOpenAI

from backend.analytics.catalog import KPI_DEFINITIONS
from backend.core.config import get_settings
from backend.schemas.analytics import AnalyticsQueryRequest, AnalyticsQueryResponse, ComparisonType
from backend.schemas.insights import FollowUpSuggestion, InsightCode, RichInsightOutput
from backend.schemas.intent import TokenUsage


INSIGHT_INSTRUCTIONS = """Write 1-3 concise management insights from only the supplied validated banking result.
Use exact values; highlight the result, material target/comparison variance, ranking, spread, or trend when present.
Do not invent causes, forecasts, recommendations, external facts, or unavailable comparisons. Maximum 65 words total.
"""


def _format(value: Decimal | None, unit: str) -> str:
    if value is None:
        return "not available"
    if unit == "INR":
        return f"₹{value / Decimal('10000000'):,.2f} crore"
    return f"{value:,.0f}"


def permitted_codes(result: AnalyticsQueryResponse) -> list[InsightCode]:
    codes = [InsightCode.ACTUAL_SUMMARY]
    if result.target_value is not None:
        codes.append(InsightCode.TARGET_PERFORMANCE)
    if result.comparison_value is not None and result.comparison != ComparisonType.NONE:
        codes.append(InsightCode.PERIOD_COMPARISON)
    return codes


def deterministic_insights(result: AnalyticsQueryResponse, codes: list[InsightCode] | None = None) -> list[str]:
    if result.row_count == 0:
        return [
            f"No records were found for {result.kpi_code.replace('_', ' ').lower()} "
            f"between {result.period_start:%b %Y} and {result.period_end:%b %Y} in your permitted scope."
        ]
    selected = codes or permitted_codes(result)
    messages: list[str] = []
    for code in selected:
        if code == InsightCode.ACTUAL_SUMMARY:
            messages.append(
                f"The reported {result.kpi_code.replace('_', ' ').lower()} is "
                f"{_format(result.actual_value, result.unit)} for {result.period_start:%b %Y} to {result.period_end:%b %Y}."
            )
        elif code == InsightCode.TARGET_PERFORMANCE and result.target_value is not None:
            relation = "above" if (result.gap_to_target or 0) > 0 else "below" if (result.gap_to_target or 0) < 0 else "equal to"
            gap = abs(result.gap_to_target or Decimal(0))
            achievement = f" Achievement is {result.achievement_percent:,.2f}%." if result.achievement_percent is not None else ""
            messages.append(f"Actual performance is {relation} target by {_format(gap, result.unit)}.{achievement}")
        elif code == InsightCode.PERIOD_COMPARISON and result.comparison_value is not None:
            growth = result.growth_percent
            if growth is None:
                messages.append(f"The {result.comparison.value.upper()} growth rate cannot be calculated because the comparison value is zero.")
            else:
                direction = "increased" if growth > 0 else "decreased" if growth < 0 else "was unchanged"
                messages.append(
                    f"Compared with {_format(result.comparison_value, result.unit)}, performance {direction} "
                    f"by {abs(growth):,.2f}% on a {result.comparison.value.upper()} basis."
                )
    return messages


async def generate_grounded_insights(client: AsyncOpenAI, result: AnalyticsQueryResponse) -> tuple[list[str], TokenUsage, bool]:
    fallback_insights = deterministic_insights(result)
    payload = {
        "kpi": result.kpi_code,
        "unit": result.unit,
        "period": [result.period_start.isoformat(), result.period_end.isoformat()],
        "actual": str(result.actual_value),
        "target": str(result.target_value) if result.target_value is not None else None,
        "gap": str(result.gap_to_target) if result.gap_to_target is not None else None,
        "achievement_pct": str(result.achievement_percent) if result.achievement_percent is not None else None,
        "comparison": result.comparison.value,
        "comparison_value": str(result.comparison_value) if result.comparison_value is not None else None,
        "growth_pct": str(result.growth_percent) if result.growth_percent is not None else None,
    }
    return await generate_rich_insights(client, payload, fallback_insights)


async def generate_rich_insights(
    client: AsyncOpenAI,
    payload: dict,
    fallback_insights: list[str],
) -> tuple[list[str], TokenUsage, bool]:
    try:
        response = await client.responses.parse(
            model=get_settings().openai_model,
            instructions=INSIGHT_INSTRUCTIONS,
            input=json.dumps(payload, separators=(",", ":"), default=str),
            text_format=RichInsightOutput,
            max_output_tokens=220,
            store=False,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise ValueError("Missing structured insights")
        insights = [item.strip() for item in parsed.insights if item.strip()]
        if not insights:
            raise ValueError("No grounded insights returned")
        raw_usage = response.usage
        usage = TokenUsage(
            input_tokens=getattr(raw_usage, "input_tokens", 0) if raw_usage else 0,
            output_tokens=getattr(raw_usage, "output_tokens", 0) if raw_usage else 0,
            total_tokens=getattr(raw_usage, "total_tokens", 0) if raw_usage else 0,
        )
        return insights, usage, False
    except Exception:
        return fallback_insights, TokenUsage(), True


def grounded_follow_ups(request: AnalyticsQueryRequest, result: AnalyticsQueryResponse) -> list[FollowUpSuggestion]:
    if result.row_count == 0:
        return []
    suggestions: list[FollowUpSuggestion] = []
    if request.comparison != ComparisonType.YOY:
        plan = request.model_copy(update={"comparison": ComparisonType.YOY})
        suggestions.append(FollowUpSuggestion(label="Compare YoY", question=f"Compare {request.kpi_code.replace('_', ' ').lower()} year on year for the same period.", analytics_request=plan))
    if request.comparison != ComparisonType.QOQ:
        plan = request.model_copy(update={"comparison": ComparisonType.QOQ})
        suggestions.append(FollowUpSuggestion(label="Compare QoQ", question=f"Compare {request.kpi_code.replace('_', ' ').lower()} quarter on quarter for the same period.", analytics_request=plan))

    related = {
        "DEPOSIT_BUSINESS_AMOUNT": "DEPOSIT_ACCOUNT_COUNT",
        "DEPOSIT_ACCOUNT_COUNT": "DEPOSIT_BUSINESS_AMOUNT",
        "ADVANCE_OUTSTANDING_AMOUNT": "ADVANCE_ACCOUNT_COUNT",
        "ADVANCE_ACCOUNT_COUNT": "ADVANCE_OUTSTANDING_AMOUNT",
        "ASSET_QUALITY_OUTSTANDING_AMOUNT": "ASSET_QUALITY_ACCOUNT_COUNT",
        "ASSET_QUALITY_ACCOUNT_COUNT": "ASSET_QUALITY_OUTSTANDING_AMOUNT",
        "DIGITAL_REGISTERED_CUSTOMERS": "DIGITAL_ACTIVE_CUSTOMERS",
        "DIGITAL_ACTIVE_CUSTOMERS": "DIGITAL_REGISTERED_CUSTOMERS",
    }.get(request.kpi_code)
    if related and related in KPI_DEFINITIONS:
        plan = request.model_copy(update={"kpi_code": related})
        suggestions.append(FollowUpSuggestion(label="Related KPI", question=f"Show {related.replace('_', ' ').lower()} for the same period and products.", analytics_request=plan))
    return suggestions[:3]
