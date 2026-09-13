import logging
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response, status

from backend.core.config import get_settings
from backend.core.logging_config import configure_logging
from backend.api.auth import router as auth_router
from backend.api.analytics import router as analytics_router
from backend.api.intent import router as intent_router
from backend.api.insights import router as insights_router
from backend.api.operations import router as operations_router
from backend.api.scope import router as scope_router
from backend.api.semantic import router as semantic_router
from backend.db.health import database_health
from backend.db.analytics_session import get_analytics_engine
from backend.db.session import get_engine


settings = get_settings()
configure_logging(settings)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info(
        "application_started name=%s environment=%s",
        settings.app_name,
        settings.environment,
    )
    try:
        yield
    finally:
        await get_analytics_engine().dispose()
        await get_engine().dispose()
        logger.info("application_stopped name=%s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description="Backend API for the local banking NL2SQL proof of concept.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(auth_router)
app.include_router(scope_router)
app.include_router(analytics_router)
app.include_router(intent_router)
app.include_router(insights_router)
app.include_router(operations_router)
app.include_router(semantic_router)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = str(uuid4())
    started = perf_counter()
    log_context = {"request_id": request_id}

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((perf_counter() - started) * 1000, 2)
        logger.exception(
            "request_failed method=%s path=%s duration_ms=%s",
            request.method,
            request.url.path,
            duration_ms,
            extra=log_context,
        )
        raise

    duration_ms = round((perf_counter() - started) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_completed method=%s path=%s status=%s duration_ms=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        extra=log_context,
    )
    return response


@app.get("/")
async def root() -> dict[str, str]:
    return {"application": "Banking NL2SQL API", "status": "running"}


@app.get("/health")
async def health(response: Response) -> dict[str, str | dict[str, str]]:
    database = await database_health()
    if database["status"] != "up":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "up" if database["status"] == "up" else "degraded",
        "database": database,
    }
