import os
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

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
    """Ensure PostgreSQL schema and test env variables are set, cleaning up test rows after yield."""
    os.environ["TESTING"] = "true"
    os.environ["SESSION_SECRET"] = TEST_SECRET
    await init_db()
    yield
    # Clean up test-created records during fixture teardown
    async with async_session() as session:
        await session.execute(
            text(
                "DELETE FROM researchusage WHERE session_id LIKE 'test-%' "
                "OR client_ip IN ('testclient', '198.51.100.42')"
            )
        )
        await session.execute(
            text(
                "DELETE FROM researchjob WHERE query LIKE '%test%' "
                "OR session_id LIKE 'test-%'"
            )
        )
        await session.commit()


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
    """Verify research history scoping, public sharing toggle, 404 private protection, and forking."""
    transport = ASGITransport(app=app)
    with patch("app.main.run_research_task", new_callable=AsyncMock):
        # User A creates a research session (private by default)
        job_a_id = None
        forked_b_id = None
        cookies_a = None
        cookies_b = None

        async with AsyncClient(transport=transport, base_url="http://test") as client_a:
            cookies_a = client_a.cookies
            create_a = await client_a.post(
                "/api/research",
                json={"query": "User A Private Study", "depth": 1, "breadth": 2},
            )
            if create_a.status_code == 200:
                job_a = create_a.json()
                job_a_id = job_a.get("id")

        try:
            assert create_a.status_code == 200
            assert job_a["is_owner"] is True
            assert job_a["is_public"] is False

            # User A lists research -> sees their own job
            async with AsyncClient(transport=transport, base_url="http://test", cookies=cookies_a) as client_a:
                list_a = await client_a.get("/api/research")
                assert list_a.status_code == 200
                assert any(j["id"] == job_a_id for j in list_a.json())

            # User B (separate client instance, distinct cookies and session)
            async with AsyncClient(transport=transport, base_url="http://test") as client_b:
                cookies_b = client_b.cookies
                # User B lists research -> User A's job MUST NOT appear in User B's history
                list_b = await client_b.get("/api/research")
                assert list_b.status_code == 200
                assert not any(j["id"] == job_a_id for j in list_b.json())

                # User B visits User A's private report URL -> 404 Not Found (private protection)
                get_private = await client_b.get(f"/api/research/{job_a_id}")
                assert get_private.status_code == 404

                # User B attempts to toggle visibility on User A's job -> 403 Forbidden
                toggle_b = await client_b.patch(
                    f"/api/research/{job_a_id}/visibility",
                    json={"is_public": True},
                )
                assert toggle_b.status_code == 403

            # User A makes the report public
            async with AsyncClient(
                transport=transport, base_url="http://test", cookies=cookies_a
            ) as client_a_return:
                toggle_a = await client_a_return.patch(
                    f"/api/research/{job_a_id}/visibility",
                    json={"is_public": True},
                )
                assert toggle_a.status_code == 200
                assert toggle_a.json()["is_public"] is True

            # Now User B visits User A's shared report -> succeeds with 200 OK
            async with AsyncClient(transport=transport, base_url="http://test", cookies=cookies_b) as client_b_view:
                get_shared = await client_b_view.get(f"/api/research/{job_a_id}")
                assert get_shared.status_code == 200
                shared_data = get_shared.json()
                assert shared_data["id"] == job_a_id
                assert shared_data["is_owner"] is False
                assert shared_data["is_public"] is True

                # Attempt fork while still queued -> rejected with 409 Conflict
                fork_active = await client_b_view.post(f"/api/research/{job_a_id}/fork")
                assert fork_active.status_code == 409
                assert "cannot be imported yet" in fork_active.json()["detail"]

            # Mark source job as running in DB
            async with async_session() as db:
                job_in_db = await db.get(ResearchJob, job_a_id)
                assert job_in_db is not None
                job_in_db.status = JobStatus.RUNNING
                await db.commit()

            # Attempt fork while running -> also rejected with 409 Conflict
            async with AsyncClient(transport=transport, base_url="http://test", cookies=cookies_b) as client_b_view:
                fork_running = await client_b_view.post(f"/api/research/{job_a_id}/fork")
                assert fork_running.status_code == 409
                assert "cannot be imported yet" in fork_running.json()["detail"]

            # Mark source job as completed in DB
            async with async_session() as db:
                job_in_db = await db.get(ResearchJob, job_a_id)
                assert job_in_db is not None
                job_in_db.status = JobStatus.COMPLETED
                job_in_db.result = "Completed study results"
                await db.commit()

            # User B can now successfully fork the completed research
            async with AsyncClient(transport=transport, base_url="http://test", cookies=cookies_b) as client_b_view:
                fork_res = await client_b_view.post(f"/api/research/{job_a_id}/fork")
                if fork_res.status_code == 200:
                    forked_data = fork_res.json()
                    forked_b_id = forked_data.get("id")

                assert fork_res.status_code == 200
                assert forked_data["id"] != job_a_id
                assert forked_data["query"] == "User A Private Study"
                assert forked_data["is_owner"] is True
                assert forked_data["is_public"] is False
                assert forked_data["status"] == "completed"

                # User B's history now contains the forked research
                list_b_after = await client_b_view.get("/api/research")
                assert list_b_after.status_code == 200
                assert any(j["id"] == forked_b_id for j in list_b_after.json())

                # User B attempts to DELETE User A's research -> strictly rejected with 403 Forbidden
                delete_attempt = await client_b_view.delete(f"/api/research/{job_a_id}")
                assert delete_attempt.status_code == 403

            # User A revokes public sharing (turns it back to private)
            async with AsyncClient(
                transport=transport, base_url="http://test", cookies=cookies_a
            ) as client_a_revoke:
                revoke_a = await client_a_revoke.patch(
                    f"/api/research/{job_a_id}/visibility",
                    json={"is_public": False},
                )
                assert revoke_a.status_code == 200
                assert revoke_a.json()["is_public"] is False

            # User B can no longer view User A's original report -> 404 Not Found
            async with AsyncClient(transport=transport, base_url="http://test", cookies=cookies_b) as client_b_denied:
                denied_res = await client_b_denied.get(f"/api/research/{job_a_id}")
                assert denied_res.status_code == 404
        finally:
            # Teardown User B's forked job independently
            if forked_b_id and cookies_b:
                try:
                    async with AsyncClient(
                        transport=transport, base_url="http://test", cookies=cookies_b
                    ) as client_b_cleanup:
                        del_fork = await client_b_cleanup.delete(f"/api/research/{forked_b_id}")
                        assert del_fork.status_code == 200
                except Exception as e:
                    print(f"Warning: Failed to cleanup forked_b_id {forked_b_id}: {e}")

            # Teardown User A's research independently
            if job_a_id and cookies_a:
                try:
                    async with AsyncClient(
                        transport=transport, base_url="http://test", cookies=cookies_a
                    ) as client_a_cleanup:
                        del_res = await client_a_cleanup.delete(f"/api/research/{job_a_id}")
                        assert del_res.status_code == 200
                        assert del_res.json()["status"] == "deleted"
                except Exception as e:
                    print(f"Warning: Failed to cleanup job_a_id {job_a_id}: {e}")


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
    with patch("app.main.run_research_task", new_callable=AsyncMock):
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

    with patch("app.main.run_research_task", new_callable=AsyncMock):
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
    monkeypatch.setenv("ALLOW_QUEUE_ONLY", "true")
    monkeypatch.setenv("TRUST_ALL_PROXIES", "true")
    monkeypatch.setenv("RATE_LIMIT_JOBS_PER_HOUR", "2")
    monkeypatch.setenv("MAX_CONCURRENT_JOBS_PER_SESSION", "0")

    headers_shared_ip = {"x-forwarded-for": "198.51.100.42"}

    with patch("app.main.run_research_task", new_callable=AsyncMock):
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


def test_get_session_secret_rejects_example_placeholders(monkeypatch):
    """Verify that get_session_secret strictly rejects all example placeholder secrets."""
    placeholders = [
        "change-this-to-a-secure-random-secret-in-production",
        "change-this-to-a-cryptographically-random-secret-in-production",
        "change-this-to-anything-else",
    ]
    for ph in placeholders:
        monkeypatch.setenv("SESSION_SECRET", ph)
        with pytest.raises(ValueError, match="example placeholder value"):
            get_session_secret()
