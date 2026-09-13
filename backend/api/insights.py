import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.analytics.query_service import AnalyticsValidationError, execute_analytics_query
from backend.auth.dependencies import CurrentUser
from backend.db.analytics_session import get_analytics_session
from backend.insights.service import deterministic_insights, generate_grounded_insights, grounded_follow_ups
from backend.llm.client import get_openai_client
from backend.rbac.scope import OrganizationAccessDenied, ScopeConfigurationError
from backend.schemas.insights import InsightRequest, InsightResponse
from backend.schemas.intent import TokenUsage
from backend.db.session import get_db_session
from backend.observability.events import record_audit, record_usage
from backend.models.conversation import ConversationSession
from sqlalchemy import select


router = APIRouter(prefix="/insights", tags=["grounded insights"])
logger = logging.getLogger(__name__)


@router.post("/generate", response_model=InsightResponse)
async def generate_insights(
    request: InsightRequest,
    access: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_analytics_session)],
    writer: Annotated[AsyncSession, Depends(get_db_session)],
) -> InsightResponse:
    try:
        result = await execute_analytics_query(session, access, request.analytics_request)
    except OrganizationAccessDenied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requested organization is outside your permitted scope") from None
    except ScopeConfigurationError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No valid organization scope is assigned") from None
    except AnalyticsValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from None

    if result.row_count == 0:
        insights, usage, fallback = deterministic_insights(result), TokenUsage(), False
    else:
        try:
            insights, usage, fallback = await generate_grounded_insights(get_openai_client(), result)
        except RuntimeError:
            insights, usage, fallback = deterministic_insights(result), TokenUsage(), True

    logger.info(
        "insights_generated user_id=%s kpi=%s empty=%s fallback=%s tokens=%s",
        access.user.id, result.kpi_code, result.row_count == 0, fallback, usage.total_tokens,
    )
    usage_session_id = None
    if request.session_id is not None:
        usage_session_id = await writer.scalar(
            select(ConversationSession.id).where(
                ConversationSession.id == request.session_id,
                ConversationSession.user_id == access.user.id,
            )
        )
    record_usage(writer, access.user.id, "insight", usage, usage_session_id)
    record_audit(writer, "INSIGHT", "SUCCESS", "/insights/generate", access.user.id, result.effective_organization_id,
                 {"kpi": result.kpi_code, "empty": result.row_count == 0, "fallback": fallback})
    await writer.commit()
    return InsightResponse(
        result=result,
        insights=insights,
        follow_ups=grounded_follow_ups(request.analytics_request, result),
        empty_result=result.row_count == 0,
        fallback_used=fallback,
        usage=usage,
    )
