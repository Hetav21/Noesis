import os
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import init_db
from app.main import app
from app.session import (
    SESSION_COOKIE_NAME,
    generate_session_id,
    sign_session_id,
    verify_session_token,
)


@pytest.fixture(autouse=True)
async def isolate_database():
    """Ensure PostgreSQL schema and test env variables are set."""
    os.environ["TESTING"] = "true"
    await init_db()
    yield


def test_session_signing_and_verification():
    session_id = generate_session_id()
    token = sign_session_id(session_id)
    assert "." in token

    # Valid token verification
    verified_id = verify_session_token(token)
    assert verified_id == session_id

    # Tampered signature should fail
    tampered = f"{token}extra"
    assert verify_session_token(tampered) is None

    # Altered session ID with original signature should fail
    parts = token.split(".", 1)
    altered = f"another-session-id.{parts[1]}"
    assert verify_session_token(altered) is None

    # Malformed token formats
    assert verify_session_token("") is None
    assert verify_session_token("invalidformat") is None
    assert verify_session_token(None) is None


@pytest.mark.asyncio
async def test_session_cookie_automatic_issuance():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Request without cookies should receive Set-Cookie
        res = await client.get("/api/session/me")
        assert res.status_code == 200
        data = res.json()
        assert "session_id" in data
        assert SESSION_COOKIE_NAME in client.cookies


@pytest.mark.asyncio
async def test_session_history_isolation_and_shareable_links():
    transport = ASGITransport(app=app)
    with patch("app.main.run_research_task"):
        # User A creates a research session
        async with AsyncClient(transport=transport, base_url="http://test") as client_a:
            create_a = await client_a.post(
                "/api/research",
                json={"query": "User A Private Study", "depth": 1, "breadth": 2},
            )
            assert create_a.status_code == 200
            job_a = create_a.json()
            job_a_id = job_a["id"]
            assert job_a["is_owner"] is True

            # User A lists research -> sees their own job
            list_a = await client_a.get("/api/research")
            assert list_a.status_code == 200
            assert any(j["id"] == job_a_id for j in list_a.json())

        # User B (separate client instance, distinct cookies and session)
        async with AsyncClient(transport=transport, base_url="http://test") as client_b:
            # User B lists research -> User A's job MUST NOT appear in User B's history
            list_b = await client_b.get("/api/research")
            assert list_b.status_code == 200
            assert not any(j["id"] == job_a_id for j in list_b.json())

            # User B visits User A's shareable report URL -> can view it, but is_owner is False
            get_shared = await client_b.get(f"/api/research/{job_a_id}")
            assert get_shared.status_code == 200
            shared_data = get_shared.json()
            assert shared_data["id"] == job_a_id
            assert shared_data["query"] == "User A Private Study"
            assert shared_data["is_owner"] is False

            # User B attempts to DELETE User A's research -> strictly rejected with 403 Forbidden
            delete_attempt = await client_b.delete(f"/api/research/{job_a_id}")
            assert delete_attempt.status_code == 403
            assert "Forbidden" in delete_attempt.json()["detail"]

        # User A returns and deletes their own research -> succeeds
        async with AsyncClient(transport=transport, base_url="http://test", cookies=client_a.cookies) as client_a_return:
            del_res = await client_a_return.delete(f"/api/research/{job_a_id}")
            assert del_res.status_code == 200
            assert del_res.json()["status"] == "deleted"


@pytest.mark.asyncio
async def test_concurrency_limit_enforcement():
    transport = ASGITransport(app=app)
    with patch("app.main.run_research_task"):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Start job 1 (remains queued)
            res1 = await client.post(
                "/api/research",
                json={"query": "First concurrent research", "depth": 1, "breadth": 2},
            )
            assert res1.status_code == 200
            job1_id = res1.json()["id"]

            # Attempt job 2 while job 1 is active -> rejected with 429
            res2 = await client.post(
                "/api/research",
                json={"query": "Second concurrent research", "depth": 1, "breadth": 2},
            )
            assert res2.status_code == 429
            assert "already in progress" in res2.json()["detail"]

            # Clean up job 1
            await client.delete(f"/api/research/{job1_id}")


@pytest.mark.asyncio
async def test_hourly_rate_limit_enforcement(monkeypatch):
    transport = ASGITransport(app=app)
    # Set hourly limit to 2 for this test
    monkeypatch.setenv("RATE_LIMIT_JOBS_PER_HOUR", "2")
    # Disable concurrency check so we specifically test the hourly window
    monkeypatch.setenv("MAX_CONCURRENT_JOBS_PER_SESSION", "0")

    with patch("app.main.run_research_task"):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created_ids = []
            try:
                # Job 1
                r1 = await client.post(
                    "/api/research",
                    json={"query": "Rate limit job 1", "depth": 1, "breadth": 2},
                )
                assert r1.status_code == 200
                created_ids.append(r1.json()["id"])

                # Job 2
                r2 = await client.post(
                    "/api/research",
                    json={"query": "Rate limit job 2", "depth": 1, "breadth": 2},
                )
                assert r2.status_code == 200
                created_ids.append(r2.json()["id"])

                # Job 3 (exceeds limit of 2) -> 429
                r3 = await client.post(
                    "/api/research",
                    json={"query": "Rate limit job 3", "depth": 1, "breadth": 2},
                )
                assert r3.status_code == 429
                assert "Rate limit exceeded" in r3.json()["detail"]
            finally:
                for jid in created_ids:
                    await client.delete(f"/api/research/{jid}")
