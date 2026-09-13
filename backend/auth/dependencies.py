from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.jwt import TokenValidationError, decode_access_token
from backend.db.session import get_db_session
from backend.repositories.users import UserAccessRecord, get_user_access


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserAccessRecord:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = decode_access_token(token)
    except TokenValidationError:
        raise credentials_error from None

    access = await get_user_access(session, user_id)
    if access is None:
        raise credentials_error
    return access


CurrentUser = Annotated[UserAccessRecord, Depends(get_current_user)]

