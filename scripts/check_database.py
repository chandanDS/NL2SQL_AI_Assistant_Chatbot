import asyncio

from sqlalchemy import text

from backend.db.session import get_engine


async def main() -> None:
    engine = get_engine()
    try:
        async with engine.connect() as connection:
            row = (
                await connection.execute(
                    text(
                        "SELECT current_database() AS database_name, "
                        "current_user AS user_name, "
                        "current_setting('server_version') AS server_version"
                    )
                )
            ).one()
        print(f"Database: {row.database_name}")
        print(f"User: {row.user_name}")
        print(f"PostgreSQL: {row.server_version}")
        print("Async SQLAlchemy connection: OK")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

