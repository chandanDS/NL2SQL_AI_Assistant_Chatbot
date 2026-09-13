from enum import StrEnum

from pydantic import BaseModel, Field

from backend.schemas.analytics import AnalyticsQueryRequest, AnalyticsQueryResponse
from backend.schemas.intent import TokenUsage
from uuid import UUID


class InsightCode(StrEnum):
    ACTUAL_SUMMARY = "actual_summary"
    TARGET_PERFORMANCE = "target_performance"
    PERIOD_COMPARISON = "period_comparison"


class InsightSelection(BaseModel):
    insight_codes: list[InsightCode] = Field(min_length=1, max_length=3)


class RichInsightOutput(BaseModel):
    insights: list[str] = Field(min_length=1, max_length=3)


class FollowUpSuggestion(BaseModel):
    label: str
    question: str
    analytics_request: AnalyticsQueryRequest


class InsightRequest(BaseModel):
    analytics_request: AnalyticsQueryRequest
    session_id: UUID | None = None


class InsightResponse(BaseModel):
    result: AnalyticsQueryResponse
    insights: list[str]
    follow_ups: list[FollowUpSuggestion]
    empty_result: bool
    fallback_used: bool
    grounding_method: str = "validated_codes_and_server_values"
    usage: TokenUsage
