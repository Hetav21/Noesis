import os
from unittest.mock import patch

import pytest

from app.db import check_db_health, get_database_url, init_db


def test_get_database_url_missing():
    with (
        patch.dict(os.environ, {}, clear=True),
        pytest.raises(
            ValueError, match="DATABASE_URL environment variable is required"
        ),
    ):
        get_database_url()


def test_get_database_url_rejects_sqlite():
    with (
        patch.dict(
            os.environ,
            {"DATABASE_URL": "sqlite+aiosqlite:///./research.db"},
            clear=True,
        ),
        pytest.raises(ValueError, match="Unsupported database scheme"),
    ):
        get_database_url()


def test_get_database_url_postgres_prefix():
    with patch.dict(
        os.environ,
        {"DATABASE_URL": "postgres://user:secret@localhost:5432/noesis_prod"},
        clear=True,
    ):
        url = get_database_url()
        assert url == "postgresql+asyncpg://user:secret@localhost:5432/noesis_prod"


def test_get_database_url_postgresql_prefix():
    with patch.dict(
        os.environ,
        {"DATABASE_URL": "postgresql://user:secret@localhost:5432/noesis_prod"},
        clear=True,
    ):
        url = get_database_url()
        assert url == "postgresql+asyncpg://user:secret@localhost:5432/noesis_prod"


def test_get_database_url_asyncpg_already():
    with patch.dict(
        os.environ,
        {"DATABASE_URL": "postgresql+asyncpg://user:secret@localhost:5432/noesis_prod"},
        clear=True,
    ):
        url = get_database_url()
        assert url == "postgresql+asyncpg://user:secret@localhost:5432/noesis_prod"


def test_get_database_url_sslmode_normalized():
    with patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://user:secret@ep-test.neon.tech/neondb?sslmode=require"
        },
        clear=True,
    ):
        url = get_database_url()
        assert (
            url
            == "postgresql+asyncpg://user:secret@ep-test.neon.tech/neondb?ssl=require"
        )


@pytest.mark.asyncio
async def test_check_db_health():
    await init_db()
    is_healthy = await check_db_health()
    assert is_healthy is True
