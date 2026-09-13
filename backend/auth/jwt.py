from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from jwt import InvalidTokenError

from backend.core.config import get_settings


class TokenValidationError(Exception):
    """Raised when an access token is missing, invalid, or expired."""


def create_access_token(*, user_id: int, username: str) -> tuple[str, int]:
    settings = get_settings()
    secret = settings.jwt_secret_key.get_secret_value()
    if len(secret) < 32:
        raise RuntimeError("JWT_SECRET_KEY must contain at least 32 characters")

    now = datetime.now(UTC)
    expires_in = settings.jwt_access_token_minutes * 60
    payload = {
        "sub": str(user_id),
        "preferred_username": username,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(seconds=expires_in),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "jti": str(uuid4()),
    }
    token = jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str) -> int:
    settings = get_settings()
    secret = settings.jwt_secret_key.get_secret_value()
    if len(secret) < 32:
        raise RuntimeError("JWT_SECRET_KEY must contain at least 32 characters")

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["sub", "iat", "nbf", "exp", "iss", "aud", "jti"]},
        )
        return int(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise TokenValidationError from exc

