import logging

from sqlalchemy import text

from backend.db.session import get_engine


logger = logging.getLogger(__name__)


async def database_health() -> dict[str, str]:
    try:
        async with get_engine().connect() as connection:
            row = (
                await connection.execute(
                    text(
                        "SELECT current_database() AS database_name, "
                        "current_setting('server_version') AS server_version"
                    )
                )
            ).one()
        return {
            "status": "up",
            "database": row.database_name,
            "server_version": row.server_version,
        }
    except Exception:
        logger.exception("database_health_check_failed")
        return {
            "status": "down",
            "database": "unavailable",
            "server_version": "unavailable",
        }
