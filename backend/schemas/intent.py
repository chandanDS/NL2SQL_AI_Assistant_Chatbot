from datetime import date
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from backend.schemas.analytics import AnalyticsQueryRequest, ComparisonType
from backend.schemas.semantic import SemanticQueryPlan


class IntentStatus(StrEnum):
    READY = "ready"
    NEEDS_CLARIFICATION = "needs_clarification"
    UNSUPPORTED = "unsupported"


class BankingModule(StrEnum):
    DEPOSITS = "DEPOSITS"
    ADVANCES = "ADVANCES"
    NPA_SMA = "NPA_SMA"
    DIGITAL = "DIGITAL"


class RequestedScope(StrEnum):
    ASSIGNED = "assigned"
    BANK_WIDE = "bank_wide"


class ExtractedIntent(BaseModel):
    status: IntentStatus
    module: BankingModule | None
    kpi_code: str | None
    period_start: date | None
    period_end: date | None
    products: list[str]
    comparison: ComparisonType
    organization_unit_id: int | None
    requested_scope: RequestedScope = RequestedScope.ASSIGNED
    confidence: float = Field(ge=0, le=1)
    missing_fields: list[str]
    clarification_question: str | None
    interpretation: str
    dynamic_query_plan: SemanticQueryPlan | None = None


class IntentRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2_000)
    session_id: UUID | None = None


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class TokenUsageBreakdown(BaseModel):
    user_input_tokens: int = 0
    routing_tokens: int = 0
    sql_generation_tokens: int = 0
    context_history_tokens: int = 0
    ai_insight_tokens: int = 0
    overall_tokens: int = 0
    component_counts_are_estimates: bool = True


class IntentResponse(BaseModel):
    session_id: UUID
    status: IntentStatus
    intent: ExtractedIntent
    clarification_question: str | None
    analytics_request: AnalyticsQueryRequest | None
    dynamic_query_plan: SemanticQueryPlan | None
    messages_used: int = Field(ge=1, le=4)
    usage: TokenUsage
    usage_breakdown: TokenUsageBreakdown
