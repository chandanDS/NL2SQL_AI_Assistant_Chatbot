import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import CurrentUser
from backend.db.session import get_db_session
from backend.rbac.scope import (
    OrganizationAccessDenied,
    ScopeConfigurationError,
    resolve_organization_scope,
)
from backend.schemas.scope import OrganizationScopeResponse, ScopedOrganizationResponse


router = APIRouter(prefix="/auth", tags=["authorization"])
logger = logging.getLogger(__name__)


@router.get("/scope", response_model=OrganizationScopeResponse)
async def organization_scope(
    access: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    organization_unit_id: Annotated[int | None, Query(gt=0)] = None,
) -> OrganizationScopeResponse:
    try:
        resolved = await resolve_organization_scope(
            session,
            access,
            requested_organization_id=organization_unit_id,
        )
    except OrganizationAccessDenied:
        logger.warning(
            "organization_scope_denied user_id=%s requested_organization_id=%s",
            access.user.id,
            organization_unit_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requested organization is outside your permitted scope",
        ) from None
    except ScopeConfigurationError:
        logger.error("organization_scope_configuration_error user_id=%s", access.user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No valid organization scope is assigned",
        ) from None

    organizations = [
        ScopedOrganizationResponse(
            id=organization.id,
            code=organization.code,
            name=organization.name,
            office_type=organization.office_type,
            parent_id=organization.parent_id,
            depth=organization.depth,
        )
        for organization in resolved.organizations
    ]
    return OrganizationScopeResponse(
        role=resolved.role,
        assigned_root_id=resolved.assigned_root_id,
        effective_root_id=resolved.effective_root_id,
        organization_count=len(organizations),
        organizations=organizations,
    )

