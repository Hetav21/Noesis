import os
import uuid
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import async_session, init_db
from app.main import app
from app.models import JobStatus, ResearchJob
from app.session import (
    SESSION_COOKIE_NAME,
    generate_session_id,
    get_session_secret,
    sign_session_id,
    verify_session_token,
)

TEST_SECRET = "test-session-secret-key-32-bytes-long-for-hmac"


@pytest.fixture(autouse=True)
async def isolate_database():
    """Ensure PostgreSQL schema and test env variables are set."""
    os.environ["TESTING"] = "true"
    os.environ["SESSION_SECRET"] = TEST_SECRET
    await init_db()
    yield


def test_session_signing_and_verification():
    """Verify HMAC signature generation, validation, and rejection of tampered tokens."""
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

    # Non-ASCII signatures should fail gracefully without unhandled exception
    non_ascii_token = f"{session_id}.sig_with_éñçødîng"
    assert verify_session_token(non_ascii_token) is None


def test_session_secret_validation(monkeypatch):
    """Verify that startup/get_session_secret fails when SESSION_SECRET is missing or placeholder."""
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    with pytest.raises(ValueError, match="SESSION_SECRET environment variable is required"):
        get_session_secret()

    monkeypatch.setenv("SESSION_SECRET", "change-this-to-a-secure-random-secret-in-production")
    with pytest.raises(ValueError, match="example placeholder value"):
        get_session_secret()


@pytest.mark.asyncio
async def test_session_cookie_automatic_issuance():
    """Verify that requests lacking session cookies receive a signed Set-Cookie."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/session/me")
        assert res.status_code == 200
        data = res.json()
        assert "session_id" in data
        assert SESSION_COOKIE_NAME in client.cookies


@pytest.mark.asyncio
async def test_session_history_isolation_and_shareable_links():
    """Verify research history scoping, shareable link viewing, and deletion protections."""
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
        async with AsyncClient(
            transport=transport, base_url="http://test", cookies=client_a.cookies
        ) as client_a_return:
            del_res = await client_a_return.delete(f"/api/research/{job_a_id}")
            assert del_res.status_code == 200
            assert del_res.json()["status"] == "deleted"


@pytest.mark.asyncio
async def test_unowned_report_deletion_rejected_and_claimable():
    """Verify that unowned legacy reports (session_id=None) cannot be deleted and can be claimed."""
    legacy_job_id = str(uuid.uuid4())
    async with async_session() as db:
        legacy_job = ResearchJob(
            id=legacy_job_id,
            query="Legacy Unowned Research",
            depth=1,
            breadth=2,
            status=JobStatus.COMPLETED,
            result="Legacy report content",
            session_id=None,
            client_ip="127.0.0.1",
        )
        db.add(legacy_job)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unowned report should not appear in generic session history
        history_res = await client.get("/api/research")
        assert not any(j["id"] == legacy_job_id for j in history_res.json())

        # 2. Deletion without ownership should be strictly forbidden (403)
        delete_res = await client.delete(f"/api/research/{legacy_job_id}")
        assert delete_res.status_code == 403
        assert "Forbidden" in delete_res.json()["detail"]

        # 3. Claiming the legacy report associates it with the active session
        claim_res = await client.post(f"/api/research/{legacy_job_id}/claim")
        assert claim_res.status_code == 200
        claimed_data = claim_res.json()
        assert claimed_data["id"] == legacy_job_id
        assert claimed_data["is_owner"] is True

        # 4. Now appears in current session history
        history_after = await client.get("/api/research")
        assert any(j["id"] == legacy_job_id for j in history_after.json())

        # 5. Owner can now delete it
        del_res = await client.delete(f"/api/research/{legacy_job_id}")
        assert del_res.status_code == 200


@pytest.mark.asyncio
async def test_concurrency_limit_enforcement():
    """Verify that concurrent jobs per session are capped at MAX_CONCURRENT_JOBS_PER_SESSION."""
    transport = ASGITransport(app=app)
    with patch("app.main.run_research_task"):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res1 = await client.post(
                "/api/research",
                json={"query": "First concurrent research", "depth": 1, "breadth": 2},
            )
            assert res1.status_code == 200
            job1_id = res1.json()["id"]

            res2 = await client.post(
                "/api/research",
                json={"query": "Second concurrent research", "depth": 1, "breadth": 2},
            )
            assert res2.status_code == 429
            assert "already in progress" in res2.json()["detail"]

            await client.delete(f"/api/research/{job1_id}")


@pytest.mark.asyncio
async def test_hourly_rate_limit_durable_across_deletions(monkeypatch):
    """Verify that deleting completed research jobs does NOT circumvent hourly limits."""
    transport = ASGITransport(app=app)
    monkeypatch.setenv("RATE_LIMIT_JOBS_PER_HOUR", "2")
    monkeypatch.setenv("MAX_CONCURRENT_JOBS_PER_SESSION", "0")

    with patch("app.main.run_research_task"):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Job 1: create and immediately delete
            r1 = await client.post(
                "/api/research",
                json={"query": "Rate limit test 1", "depth": 1, "breadth": 2},
            )
            assert r1.status_code == 200
            jid1 = r1.json()["id"]
            await client.delete(f"/api/research/{jid1}")

            # Job 2: create and immediately delete
            r2 = await client.post(
                "/api/research",
                json={"query": "Rate limit test 2", "depth": 1, "breadth": 2},
            )
            assert r2.status_code == 200
            jid2 = r2.json()["id"]
            await client.delete(f"/api/research/{jid2}")

            # Job 3: Even though both ResearchJobs are deleted, ResearchUsage prevents reset
            r3 = await client.post(
                "/api/research",
                json={"query": "Rate limit test 3", "depth": 1, "breadth": 2},
            )
            assert r3.status_code == 429
            assert "Rate limit exceeded" in r3.json()["detail"]


@pytest.mark.asyncio
async def test_shared_ip_rate_limiting_with_testing_false(monkeypatch):
    """Verify that separate sessions sharing a non-loopback IP are capped by the shared IP limit."""
    transport = ASGITransport(app=app)
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.setenv("TRUST_ALL_PROXIES", "true")
    monkeypatch.setenv("RATE_LIMIT_JOBS_PER_HOUR", "2")
    monkeypatch.setenv("MAX_CONCURRENT_JOBS_PER_SESSION", "0")

    headers_shared_ip = {"x-forwarded-for": "198.51.100.42"}

    with patch("app.main.run_research_task"):
        # Session A creates 1 job from shared IP (within session limit of 2)
        async with AsyncClient(transport=transport, base_url="http://test", headers=headers_shared_ip) as client_a:
            r_a1 = await client_a.post(
                "/api/research",
                json={"query": "Session A job", "depth": 1, "breadth": 2},
            )
            assert r_a1.status_code == 200

        # Session B creates 1 job from same shared IP (total IP jobs = 2)
        async with AsyncClient(transport=transport, base_url="http://test", headers=headers_shared_ip) as client_b:
            r_b1 = await client_b.post(
                "/api/research",
                json={"query": "Session B job 1", "depth": 1, "breadth": 2},
            )
            assert r_b1.status_code == 200

            # Session B tries to create another job -> IP hourly threshold (2) is breached -> 429
            r_b2 = await client_b.post(
                "/api/research",
                json={"query": "Session B job 2", "depth": 1, "breadth": 2},
            )
            assert r_b2.status_code == 429
            assert "Rate limit exceeded" in r_b2.json()["detail"]
