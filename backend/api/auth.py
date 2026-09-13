import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import CurrentUser
from backend.auth.jwt import create_access_token
from backend.auth.password import DUMMY_PASSWORD_HASH, verify_password
from backend.db.session import get_db_session
from backend.repositories.users import get_user_by_username
from backend.observability.events import record_audit
from backend.schemas.auth import CurrentUserResponse, TokenResponse


router = APIRouter(prefix="/auth", tags=["authentication"])
logger = logging.getLogger(__name__)


@router.post("/login", response_model=TokenResponse)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    user = await get_user_by_username(session, form.username)
    candidate_hash = user.password_hash if user else DUMMY_PASSWORD_HASH
    password_valid = verify_password(form.password, candidate_hash)
    if user is None or not password_valid or not user.is_active:
        record_audit(session, "LOGIN", "DENIED", "/auth/login", user_id=user.id if user else None, details={"username": form.username[:80]})
        await session.commit()
        logger.warning("login_failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token, expires_in = create_access_token(user_id=user.id, username=user.username)
    record_audit(session, "LOGIN", "SUCCESS", "/auth/login", user_id=user.id)
    await session.commit()
    logger.info("login_succeeded user_id=%s", user.id)
    return TokenResponse(
        access_token=access_token,
        expires_in=expires_in,
        must_change_password=user.must_change_password,
    )


@router.get("/me", response_model=CurrentUserResponse)
async def current_user(access: CurrentUser) -> CurrentUserResponse:
    user = access.user
    return CurrentUserResponse(
        id=user.id,
        employee_id=user.employee_id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=access.role_code,
        organization_unit_id=access.organization_unit_id,
        organization_code=access.organization_code,
        organization_name=access.organization_name,
        office_type=access.office_type,
        must_change_password=user.must_change_password,
    )
