from functools import lru_cache
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.core.config import get_settings


@lru_cache
def get_analytics_engine() -> AsyncEngine:
    settings = get_settings()
    if not settings.analytics_database_url:
        raise RuntimeError("ANALYTICS_DATABASE_URL is not configured")
    return create_async_engine(
        settings.analytics_database_url,
        pool_pre_ping=True,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        connect_args={
            "timeout": settings.database_connect_timeout_seconds,
            "server_settings": {
                "default_transaction_read_only": "on",
                "statement_timeout": str(settings.analytics_statement_timeout_ms),
                "application_name": "banking_nl2sql_analytics",
            },
        },
    )


@lru_cache
def get_analytics_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_analytics_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_analytics_session() -> AsyncIterator[AsyncSession]:
    async with get_analytics_session_factory()() as session:
        yield session

