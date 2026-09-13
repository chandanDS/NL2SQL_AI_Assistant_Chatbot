import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.analytics.query_service import AnalyticsValidationError, execute_analytics_query
from backend.auth.dependencies import CurrentUser
from backend.db.analytics_session import get_analytics_session
from backend.rbac.scope import OrganizationAccessDenied, ScopeConfigurationError
from backend.schemas.analytics import AnalyticsQueryRequest, AnalyticsQueryResponse


router = APIRouter(prefix="/analytics", tags=["deterministic analytics"])
logger = logging.getLogger(__name__)


@router.post("/query", response_model=AnalyticsQueryResponse)
async def query_approved_kpi(
    request: AnalyticsQueryRequest,
    access: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_analytics_session)],
) -> AnalyticsQueryResponse:
    try:
        result = await execute_analytics_query(session, access, request)
    except OrganizationAccessDenied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requested organization is outside your permitted scope") from None
    except ScopeConfigurationError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No valid organization scope is assigned") from None
    except AnalyticsValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from None

    logger.info(
        "analytics_query user_id=%s kpi=%s period_start=%s period_end=%s organization_id=%s comparison=%s rows=%s",
        access.user.id,
        request.kpi_code,
        request.period_start,
        request.period_end,
        result.effective_organization_id,
        request.comparison,
        result.row_count,
    )
    return result
