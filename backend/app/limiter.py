import os
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import and_, func, or_, select

from app.models import JobStatus, ResearchJob


def get_rate_limit_settings() -> tuple[int, int]:
    """Retrieve rate limit settings from environment variables."""
    max_concurrent = int(os.getenv("MAX_CONCURRENT_JOBS_PER_SESSION", "1"))
    hourly_limit = int(os.getenv("RATE_LIMIT_JOBS_PER_HOUR", "5"))
    return max_concurrent, hourly_limit


async def check_rate_limits(
    db: AsyncSession,
    session_id: str,
    client_ip: str,
) -> None:
    """Enforce concurrency caps and hourly sliding window rate limits.

    Raises HTTPException(429) if either threshold is breached.
    """
    max_concurrent, hourly_limit = get_rate_limit_settings()
    is_testing = os.getenv("TESTING", "").lower() in ("true", "1")

    # 1. Concurrency Check: Active research jobs in progress
    if max_concurrent > 0:
        session_active_conditions = [
            ResearchJob.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]),
            ResearchJob.session_id == session_id,
        ]

        active_query = select(func.count(ResearchJob.id)).where(
            and_(*session_active_conditions)
        )
        res = await db.execute(active_query)
        active_count = res.scalar() or 0

        # Also check IP-based concurrency in production if client_ip is non-loopback
        ip_active_count = 0
        if not is_testing and client_ip and client_ip not in ("127.0.0.1", "localhost", "testclient"):
            ip_query = select(func.count(ResearchJob.id)).where(
                and_(
                    ResearchJob.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]),
                    ResearchJob.client_ip == client_ip,
                )
            )
            ip_res = await db.execute(ip_query)
            ip_active_count = ip_res.scalar() or 0

        if active_count >= max_concurrent or ip_active_count >= max_concurrent:
            raise HTTPException(
                status_code=429,
                detail=(
                    "A research session is already in progress for your session. "
                    "Please wait for it to complete before starting a new one."
                ),
                headers={"Retry-After": "30"},
            )

    # 2. Hourly Rate Limit Check
    if hourly_limit > 0:
        one_hour_ago = datetime.now(UTC) - timedelta(hours=1)

        hourly_query = select(func.count(ResearchJob.id)).where(
            and_(
                ResearchJob.created_at >= one_hour_ago,
                ResearchJob.session_id == session_id,
            )
        )
        res = await db.execute(hourly_query)
        session_hourly_count = res.scalar() or 0

        # Also check IP-based hourly count in production
        ip_hourly_count = 0
        if not is_testing and client_ip and client_ip not in ("127.0.0.1", "localhost", "testclient"):
            ip_query = select(func.count(ResearchJob.id)).where(
                and_(
                    ResearchJob.created_at >= one_hour_ago,
                    ResearchJob.client_ip == client_ip,
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
