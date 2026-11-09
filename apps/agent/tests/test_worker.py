import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from sqlmodel import text

from app.db import async_session, init_db
from app.main import app

TEST_SECRET = "test-agent-internal-secret-32-bytes"


@pytest.fixture(autouse=True)
async def setup_test_env():
    os.environ["TESTING"] = "true"
    os.environ["AGENT_INTERNAL_SECRET"] = TEST_SECRET
    os.environ["ENABLE_QUEUE_POLLER"] = "false"
    await init_db()
    yield
    async with async_session() as session:
        await session.execute(
            text("DELETE FROM researchjob WHERE query LIKE 'Test%' OR id LIKE 'job-test-%'")
        )
        await session.commit()


@pytest.mark.asyncio
async def test_agent_health():
    """Verify agent health endpoint reports service name and liveness."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["service"] == "noesis-agent"
        assert "status" in data


@pytest.mark.asyncio
async def test_dispatch_auth_required():
    """Verify that dispatch requires valid internal secret header."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Lacking authorization
        res = await client.post(
            "/api/jobs/dispatch",
            json={"job_id": "job-123", "query": "Test query"},
        )
        assert res.status_code == 401

        # With invalid secret
        res = await client.post(
            "/api/jobs/dispatch",
            json={"job_id": "job-123", "query": "Test query"},
            headers={"X-Internal-Secret": "wrong-secret"},
        )
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_dispatch_accepted_with_secret():
    """Verify that dispatch succeeds and returns 202 Accepted when authorized."""
    transport = ASGITransport(app=app)
    with patch("app.main.run_research_task", new_callable=AsyncMock):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/api/jobs/dispatch",
                json={"job_id": "job-test-456", "query": "Test quantum mechanics"},
                headers={"X-Internal-Secret": TEST_SECRET},
            )
            assert res.status_code == 202
            data = res.json()
            assert data["status"] == "accepted"
            assert data["job_id"] == "job-test-456"


@pytest.mark.asyncio
async def test_cancel_job_via_payload():
    """Verify cancellation endpoint accepts json payload with authorization."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Without secret -> 401
        res = await client.post(
            "/api/jobs/cancel",
            json={"job_id": "job-test-nonexistent"},
        )
        assert res.status_code == 401

        # With secret but nonexistent job -> 404
        res = await client.post(
            "/api/jobs/cancel",
            json={"job_id": "job-test-nonexistent"},
            headers={"X-Internal-Secret": TEST_SECRET},
        )
        assert res.status_code == 404

