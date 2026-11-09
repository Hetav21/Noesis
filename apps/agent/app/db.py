import os
import re
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel, text

load_dotenv()


def get_database_url() -> str:
    """Retrieve and normalize DATABASE_URL for asyncpg compatibility with Neon PostgreSQL."""
    raw_url = os.getenv("DATABASE_URL", "").strip()
    if not raw_url:
        raise ValueError(
            "DATABASE_URL environment variable is required. Please configure a Neon PostgreSQL connection string."
        )

    # Normalize standard PostgreSQL URL schemes for asyncpg compatibility
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif raw_url.startswith("postgresql://") and not raw_url.startswith("postgresql+"):
        raw_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    if not raw_url.startswith("postgresql+asyncpg://"):
        raise ValueError(
            f"Unsupported database scheme: '{raw_url.split('://')[0]}'. "
            "Only Neon PostgreSQL (postgresql+asyncpg://) is supported."
        )

    # asyncpg expects 'ssl' instead of libpq's 'sslmode' query parameter
    raw_url = re.sub(r"([?&])sslmode=", r"\1ssl=", raw_url)

    return raw_url


DATABASE_URL = get_database_url()

engine_kwargs: dict = {
    "echo": os.getenv("SQL_ECHO", "false").lower() == "true",
    "future": True,
}

if (
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
    """Initialize database tables and run idempotent migrations for session tracking."""
    async with engine.begin() as conn:
        # Acquire transaction-scoped advisory lock to serialize startup schema changes across concurrent workers
        if conn.dialect.name == "postgresql":
            await conn.execute(text("SELECT pg_advisory_xact_lock(424242);"))

        await conn.run_sync(SQLModel.metadata.create_all)
        # Ensure new session and IP tracking columns exist on pre-existing tables
        await conn.execute(
            text("ALTER TABLE researchjob ADD COLUMN IF NOT EXISTS session_id VARCHAR;")
        )
        await conn.execute(
            text("ALTER TABLE researchjob ADD COLUMN IF NOT EXISTS client_ip VARCHAR;")
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_researchjob_session_id ON researchjob (session_id);"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_researchjob_client_ip ON researchjob (client_ip);"
            )
        )


async def check_db_health() -> bool:
    """Execute a simple query to verify database liveness."""
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        return False


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session."""
    async with async_session() as session:
        yield session
