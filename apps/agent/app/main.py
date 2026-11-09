import asyncio
import os
import traceback
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel
from sqlmodel import select

from app.db import async_session, check_db_health, init_db
from app.models import JobStatus, ResearchJob
from app.services.research import ResearchWorkflow

# Track actively running research jobs in memory
_active_jobs: dict[str, asyncio.Task] = {}


def verify_internal_secret(
    x_internal_secret: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> bool:
    """Validate internal service-to-service secret for webhook dispatches."""
    expected_secret = os.getenv("AGENT_INTERNAL_SECRET", "").strip() or os.getenv(
        "INTERNAL_SERVICE_KEY", ""
    ).strip()

    # If no secret is configured in the environment (e.g. local dev), allow requests
    if not expected_secret:
        return True

    # Check X-Internal-Secret header
    if x_internal_secret and x_internal_secret == expected_secret:
        return True

    # Check Authorization: Bearer <token> header
    if authorization:
        parts = authorization.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1] == expected_secret:
            return True

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized: Invalid internal service secret",
    )


async def run_research_task(
    job_id: str,
    query: str,
    depth: int,
    breadth: int,
    session_id: str | None = None,
    client_ip: str | None = None,
) -> None:
    """Execute autonomous multi-agent research pipeline and persist progress to PostgreSQL."""
    session_factory = async_session
    try:
        async with session_factory() as db:
            result = await db.execute(select(ResearchJob).where(ResearchJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                print(f"[Agent] Job {job_id} not found in database, skipping")
                return

            job.status = JobStatus.RUNNING
            job.logs = [
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "message": "Research started by Noesis Agent",
                    "level": "info",
                }
            ]
            await db.commit()

        async def log_callback(log_entry: dict):
            """Stream log entries to database."""
            async with session_factory() as update_db:
                res = await update_db.execute(
                    select(ResearchJob).where(ResearchJob.id == job_id)
                )
                curr_job = res.scalar_one_or_none()
                if curr_job:
                    logs = curr_job.logs
                    log_entry["timestamp"] = datetime.now(UTC).isoformat()
                    logs.append(log_entry)
                    curr_job.logs = logs
                    await update_db.commit()

        workflow = ResearchWorkflow(
            query=query, log_callback=log_callback, depth=depth, breadth=breadth
        )
        final_result = await workflow.research()

        async with session_factory() as final_db:
            result = await final_db.execute(
                select(ResearchJob).where(ResearchJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            if job:
                job.status = JobStatus.COMPLETED
                job.result = final_result
                logs = job.logs
                logs.append(
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "message": "Research completed successfully",
                        "level": "success",
                    }
                )
                job.logs = logs
                await final_db.commit()

    except asyncio.CancelledError:
        print(f"[Agent] Job {job_id} was cancelled")
        async with session_factory() as cancel_db:
            result = await cancel_db.execute(
                select(ResearchJob).where(ResearchJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            if job and job.status != JobStatus.COMPLETED:
                job.status = JobStatus.FAILED
                job.result = "Job was cancelled."
                logs = job.logs
                logs.append(
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "message": "Job execution cancelled",
                        "level": "warning",
                    }
                )
                job.logs = logs
                await cancel_db.commit()
        raise

    except Exception as e:  # noqa: BLE001
        print(f"[Agent] Error in research task {job_id}: {e}")
        traceback.print_exc()
        async with session_factory() as err_db:
            result = await err_db.execute(
                select(ResearchJob).where(ResearchJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            if job and job.status != JobStatus.COMPLETED:
                job.status = JobStatus.FAILED
                job.result = f"Error: {e!s}"
                logs = job.logs
                logs.append(
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "message": f"Job failed: {e!s}",
                        "level": "error",
                    }
                )
                job.logs = logs
                await err_db.commit()
    finally:
        _active_jobs.pop(job_id, None)


async def queue_worker_loop():
    """Background polling worker loop to pick up any orphaned or queued jobs."""
    poll_interval = int(os.getenv("AGENT_POLL_INTERVAL_SECONDS", "8"))
    while True:
        try:
            await asyncio.sleep(poll_interval)
            async with async_session() as db:
                result = await db.execute(
                    select(ResearchJob)
                    .where(ResearchJob.status == JobStatus.QUEUED)
                    .order_by(ResearchJob.created_at.asc())
                    .limit(1)
                )
                job = result.scalar_one_or_none()
                if job and job.id and job.id not in _active_jobs:
                    print(f"[Agent Worker] Found queued job {job.id}: '{job.query}'")
                    task = asyncio.create_task(
                        run_research_task(
                            job_id=job.id,
                            query=job.query,
                            depth=job.depth,
                            breadth=job.breadth,
                            session_id=job.session_id,
                            client_ip=job.client_ip,
                        )
                    )
                    _active_jobs[job.id] = task
        except asyncio.CancelledError:
            break
        except Exception as e:  # noqa: BLE001
            print(f"[Agent Worker] Polling loop error: {e}")
            await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB and manage background queue consumer lifecycle."""
    await init_db()
    poller_task = None
    if os.getenv("ENABLE_QUEUE_POLLER", "true").lower() in ("true", "1"):
        poller_task = asyncio.create_task(queue_worker_loop())

    yield

    if poller_task:
        poller_task.cancel()
        try:
            await poller_task
        except asyncio.CancelledError:
            # Expected when the background queue poller task is cancelled on app shutdown
            pass

    # Cancel any active running jobs on shutdown
    for job_id, task in list(_active_jobs.items()):
        task.cancel()


app = FastAPI(
    title="Noesis Agent Engine",
    description="Autonomous multi-agent research execution service",
    version="0.2.0",
    lifespan=lifespan,
)


@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Liveness probe reporting agent service and database connectivity."""
    db_ok = await check_db_health()
    return {
        "status": "ok" if db_ok else "degraded",
        "service": "noesis-agent",
        "active_jobs_count": len(_active_jobs),
        "database": "connected" if db_ok else "disconnected",
        "timestamp": datetime.now(UTC).isoformat(),
    }


class DispatchJobRequest(BaseModel):
    job_id: str
    query: str | None = None
    depth: int = 2
    breadth: int = 4
    session_id: str | None = None
    client_ip: str | None = None


@app.post("/api/jobs/dispatch", status_code=status.HTTP_202_ACCEPTED)
async def dispatch_job(
    req: DispatchJobRequest,
    _auth: bool = Depends(verify_internal_secret),
):
    """Receive dispatched research job from REST API and trigger execution asynchronously."""
    if req.job_id in _active_jobs:
        return {"status": "already_running", "job_id": req.job_id}

    query_text = req.query
    depth = req.depth
    breadth = req.breadth

    # If query not supplied in request, read from DB
    if not query_text:
        async with async_session() as db:
            result = await db.execute(
                select(ResearchJob).where(ResearchJob.id == req.job_id)
            )
            job = result.scalar_one_or_none()
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            query_text = job.query
            depth = job.depth
            breadth = job.breadth

    task = asyncio.create_task(
        run_research_task(
            job_id=req.job_id,
            query=query_text,
            depth=depth,
            breadth=breadth,
            session_id=req.session_id,
            client_ip=req.client_ip,
        )
    )
    _active_jobs[req.job_id] = task

    return {"status": "accepted", "job_id": req.job_id}


@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    _auth: bool = Depends(verify_internal_secret),
):
    """Cancel an in-flight research execution."""
    task = _active_jobs.get(job_id)
    if not task:
        raise HTTPException(status_code=404, detail="Job not actively executing")

    task.cancel()
    return {"status": "cancelled", "job_id": job_id}
