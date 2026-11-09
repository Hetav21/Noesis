import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel, text


def get_database_url() -> str:
    raw_url = os.getenv("DATABASE_URL", "").strip()
    if not raw_url:
        return "sqlite+aiosqlite:///./research.db"

    # Normalize standard PostgreSQL URL schemes for asyncpg compatibility
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif raw_url.startswith("postgresql://") and not raw_url.startswith("postgresql+"):
        raw_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # asyncpg expects 'ssl' instead of libpq's 'sslmode' query parameter
    if "sslmode=" in raw_url:
        raw_url = raw_url.replace("sslmode=", "ssl=")

    return raw_url


DATABASE_URL = get_database_url()

engine_kwargs: dict = {
    "echo": os.getenv("SQL_ECHO", "false").lower() == "true",
    "future": True,
}

if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
elif (
    "-pooler" in DATABASE_URL
    or os.getenv("DB_USE_NULL_POOL", "").lower() in ("true", "1")
    or os.getenv("TESTING", "").lower() in ("true", "1")
):
    # Neon PgBouncer pooled endpoints and test suites use NullPool to avoid multi-loop conflicts
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs.update(
        {
            "pool_pre_ping": True,
            "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
        }
    )


engine = create_async_engine(DATABASE_URL, **engine_kwargs)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def check_db_health() -> bool:
    """Execute a simple query to verify database liveness."""
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        return False


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
