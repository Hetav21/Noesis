import asyncio
import os
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import and_, func, select

from app.models import JobStatus, ResearchJob, ResearchUsage

# Global lock to serialize quota checking and job insertion across concurrent requests
rate_limit_lock = asyncio.Lock()

# In-memory tracking of live running workflows (active until background task completes)
_active_workflows: set[str] = set()
_session_active_workflows: dict[str, set[str]] = defaultdict(set)
_ip_active_workflows: dict[str, set[str]] = defaultdict(set)


def register_active_workflow(job_id: str, session_id: str | None, client_ip: str | None) -> None:
    """Register a research workflow as actively running in memory.

    Args:
        job_id: The ID of the research job.
        session_id: The owner session ID if known.
        client_ip: The originating client IP if known.
    """
    _active_workflows.add(job_id)
    if session_id:
        _session_active_workflows[session_id].add(job_id)
    if client_ip:
        _ip_active_workflows[client_ip].add(job_id)


def unregister_active_workflow(job_id: str, session_id: str | None, client_ip: str | None) -> None:
    """Unregister an active research workflow upon completion or failure.

    Args:
        job_id: The ID of the completed or failed job.
        session_id: The owner session ID if known.
        client_ip: The originating client IP if known.
    """
    _active_workflows.discard(job_id)
    if session_id and session_id in _session_active_workflows:
        _session_active_workflows[session_id].discard(job_id)
        if not _session_active_workflows[session_id]:
            _session_active_workflows.pop(session_id, None)
    if client_ip and client_ip in _ip_active_workflows:
        _ip_active_workflows[client_ip].discard(job_id)
        if not _ip_active_workflows[client_ip]:
            _ip_active_workflows.pop(client_ip, None)


def get_active_memory_count(session_id: str, client_ip: str) -> tuple[int, int]:
    """Get count of actively running background workflows in memory.

    Args:
        session_id: Active session identifier.
        client_ip: Client IP address.

    Returns:
        A tuple of (session_active_count, ip_active_count).
    """
    session_count = len(_session_active_workflows.get(session_id, set()))
    ip_count = len(_ip_active_workflows.get(client_ip, set()))
    return session_count, ip_count


def get_rate_limit_settings() -> tuple[int, int]:
    """Retrieve rate limit settings from environment variables.

    Returns:
        A tuple of (max_concurrent_jobs, hourly_jobs_limit).
    """
    max_concurrent = int(os.getenv("MAX_CONCURRENT_JOBS_PER_SESSION", "1"))
    hourly_limit = int(os.getenv("RATE_LIMIT_JOBS_PER_HOUR", "5"))
    return max_concurrent, hourly_limit


async def record_research_usage(
    db: AsyncSession,
    session_id: str,
    client_ip: str,
) -> None:
    """Record a durable usage entry for rate-limit tracking.

    Persisted in ResearchUsage table so deleting ResearchJob rows does not reset quotas.

    Args:
        db: Active async database session.
        session_id: Active session identifier.
        client_ip: Originating client IP.
    """
    usage = ResearchUsage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        client_ip=client_ip,
        created_at=datetime.now(UTC),
    )
    db.add(usage)


async def check_rate_limits(
    db: AsyncSession,
    session_id: str,
    client_ip: str,
) -> None:
    """Enforce active concurrency caps and sliding-window hourly rate limits.

    Reconciles stale or orphaned jobs in QUEUED/RUNNING states and checks both
    in-database rows and live in-memory workflow instances.

    Args:
        db: Active async database session.
        session_id: Active session identifier.
        client_ip: Originating client IP.

    Raises:
        HTTPException(429): If either concurrency or hourly limits are breached.
    """
    max_concurrent, hourly_limit = get_rate_limit_settings()
    is_testing = os.getenv("TESTING", "").lower() in ("true", "1")

    # 1. Concurrency Check: Active research jobs in progress
    if max_concurrent > 0:
        # Ignore jobs older than 15 minutes that are not in memory (orphaned/stuck)
        stale_threshold = datetime.now(UTC) - timedelta(minutes=15)

        session_active_conditions = [
            ResearchJob.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]),
            ResearchJob.session_id == session_id,
            ResearchJob.created_at >= stale_threshold,
        ]

        active_query = select(func.count(ResearchJob.id)).where(
            and_(*session_active_conditions)
        )
        res = await db.execute(active_query)
        db_session_active = res.scalar() or 0

        # Memory workflow count (covers jobs whose rows might have been deleted mid-run)
        mem_session_active, mem_ip_active = get_active_memory_count(session_id, client_ip)
        total_session_active = max(db_session_active, mem_session_active)

        # Also check IP-based concurrency if client_ip is non-loopback
        is_loopback = client_ip in ("127.0.0.1", "localhost", "::1", "testclient")
        total_ip_active = 0
        if not is_testing and client_ip and not is_loopback:
            ip_query = select(func.count(ResearchJob.id)).where(
                and_(
                    ResearchJob.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]),
                    ResearchJob.client_ip == client_ip,
                    ResearchJob.created_at >= stale_threshold,
                )
            )
            ip_res = await db.execute(ip_query)
            db_ip_active = ip_res.scalar() or 0
            total_ip_active = max(db_ip_active, mem_ip_active)

        if total_session_active >= max_concurrent or total_ip_active >= max_concurrent:
            raise HTTPException(
                status_code=429,
                detail=(
                    "A research session is already in progress for your session. "
                    "Please wait for it to complete before starting a new one."
                ),
                headers={"Retry-After": "30"},
            )

    # 2. Hourly Rate Limit Check (Queried from durable ResearchUsage table)
    if hourly_limit > 0:
        one_hour_ago = datetime.now(UTC) - timedelta(hours=1)

        hourly_query = select(func.count(ResearchUsage.id)).where(
            and_(
                ResearchUsage.created_at >= one_hour_ago,
                ResearchUsage.session_id == session_id,
            )
        )
        res = await db.execute(hourly_query)
        session_hourly_count = res.scalar() or 0

        is_loopback = client_ip in ("127.0.0.1", "localhost", "::1", "testclient")
        ip_hourly_count = 0
        if not is_testing and client_ip and not is_loopback:
            ip_query = select(func.count(ResearchUsage.id)).where(
                and_(
                    ResearchUsage.created_at >= one_hour_ago,
                    ResearchUsage.client_ip == client_ip,
                )
            )
            ip_res = await db.execute(ip_query)
            ip_hourly_count = ip_res.scalar() or 0

        if session_hourly_count >= hourly_limit or ip_hourly_count >= hourly_limit:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Maximum {hourly_limit} research jobs per hour.",
                headers={"Retry-After": "3600"},
            )
