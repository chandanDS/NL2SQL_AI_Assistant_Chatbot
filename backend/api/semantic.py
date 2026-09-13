import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.analytics.semantic_service import SemanticValidationError, execute_semantic_query
from backend.auth.dependencies import CurrentUser
from backend.db.analytics_session import get_analytics_session
from backend.db.session import get_db_session
from backend.observability.events import record_audit
from backend.observability.events import record_usage
from backend.insights.service import generate_rich_insights
from backend.llm.client import get_openai_client
from backend.models.conversation import ConversationSession
from backend.rbac.scope import OrganizationAccessDenied, ScopeConfigurationError
from backend.schemas.semantic import SemanticQueryRequest, SemanticQueryResponse


router = APIRouter(prefix="/semantic", tags=["governed dynamic NL2SQL"])
logger = logging.getLogger(__name__)


@router.post("/query", response_model=SemanticQueryResponse)
async def query_semantic_layer(
    request: SemanticQueryRequest,
    access: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_analytics_session)],
    writer: Annotated[AsyncSession, Depends(get_db_session)],
) -> SemanticQueryResponse:
    try:
        response = await execute_semantic_query(session, access, request.plan)
    except OrganizationAccessDenied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requested organization is outside your permitted scope") from None
    except ScopeConfigurationError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No valid organization scope is assigned") from None
    except SemanticValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from None
    deterministic_fallback = response.insights
    if response.row_count:
        compact_payload = {
            "module": response.module,
            "operation": response.operation,
            "unit": response.unit,
            "interpretation": response.interpretation,
            "row_count": response.row_count,
            "rows": response.rows[:10],
            "rows_truncated": response.row_count > 10,
        }
        try:
            insights, insight_usage, fallback = await generate_rich_insights(
                get_openai_client(), compact_payload, deterministic_fallback
            )
        except RuntimeError:
            insights, insight_usage, fallback = deterministic_fallback, None, True
        response.insights = insights
        response.insight_fallback_used = fallback
        if insight_usage is not None:
            response.insight_usage = insight_usage.model_dump()
            usage_session_id = None
            if request.session_id is not None:
                usage_session_id = await writer.scalar(
                    select(ConversationSession.id).where(
                        ConversationSession.id == request.session_id,
                        ConversationSession.user_id == access.user.id,
                    )
                )
            record_usage(writer, access.user.id, "semantic_insight", insight_usage, usage_session_id)
    record_audit(
        writer, "DYNAMIC_QUERY", "SUCCESS", "/semantic/query", access.user.id,
        response.effective_organization_id,
        {
            "module": request.plan.module,
            "operation": request.plan.operation,
            "measure": request.plan.measure,
            "secondary_measure": request.plan.secondary_measure,
            "group_by": request.plan.group_by,
            "row_count": response.row_count,
            "insight_fallback": response.insight_fallback_used,
        },
    )
    await writer.commit()
    logger.info("semantic_query user_id=%s module=%s operation=%s rows=%s", access.user.id, response.module, response.operation, response.row_count)
    return response
