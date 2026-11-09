import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import desc, select

from app.db import check_db_health, get_session, init_db
from app.dispatcher import dispatch_research_job
from app.limiter import (
    check_rate_limits,
    rate_limit_lock,
    record_research_usage,
    register_active_workflow,
    unregister_active_workflow,
)
from app.models import JobStatus, ResearchJob, ResearchJobCreate, ResearchJobRead
from app.session import ClientIpDep, SessionIdDep

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup table initialization."""
    await init_db()
    yield


app = FastAPI(
    title="Noesis API",
    description="Autonomous multi-agent research and synthesis engine",
    version="0.2.0",
    lifespan=lifespan,
)

# Configure CORS origins
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
]
extra_origins = os.getenv("ALLOWED_ORIGINS", "") or os.getenv("CORS_ORIGINS", "")
if extra_origins:
    for o in extra_origins.split(","):
        cleaned = o.strip()
        if cleaned and cleaned not in allowed_origins:
            allowed_origins.append(cleaned)

# Support custom origin regex or default to localhost and *.vercel.app deployments
cors_regex = os.getenv(
    "CORS_ORIGIN_REGEX",
    r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$|^https://.*\.vercel\.app$",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=cors_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Verify backend API liveness and PostgreSQL database connectivity."""
    db_ok = await check_db_health()
    return {
        "status": "ok" if db_ok else "degraded",
        "service": "noesis",
        "database": "connected" if db_ok else "disconnected",
        "timestamp": datetime.now(UTC).isoformat(),
    }


# In-memory cache for research suggestions
_suggestions_cache = {
    "key": "",
    "suggestions": [],
    "timestamp": 0.0,
}
_suggestions_inflight: dict[str, asyncio.Task] = {}


@app.get("/api/session/me")
async def get_current_session(
    session_id: SessionIdDep,
    client_ip: ClientIpDep,
):
    """Return the current verified session identifier and client IP."""
    return {
        "session_id": session_id,
        "client_ip": client_ip,
    }


@app.get("/api/suggestions")
async def get_suggestions(
    db: SessionDep,
    session_id: SessionIdDep,
    refresh: bool = Query(default=False),
):
    """Generate dynamic research suggestions based on previous research topics.

    Scopes topics to the active session to avoid cross-user query exposure.
    Cached by recent queries key for performance.
    """
    import time

    default_suggestions = [
        "Solid-state vs sodium-ion battery commercial viability",
        "Post-quantum cryptography migration for TLS 1.3",
        "Agentic orchestration patterns vs deterministic DAGs",
        "WebAssembly component model in serverless runtimes",
    ]
    try:
        result = await db.execute(
            select(ResearchJob.query)
            .where(ResearchJob.session_id == session_id)
            .order_by(desc(ResearchJob.created_at))
            .limit(6)
        )
        recent_queries = [r[0] for r in result.all() if r[0]]
        api_key = os.getenv("OPENAI_API_KEY")
        if not recent_queries or not api_key:
            return {"suggestions": default_suggestions}

        cache_key = f"{session_id}:" + "|".join(recent_queries[:5])
        # Return cached suggestions if available and not explicitly refreshing
        if (
            not refresh
            and _suggestions_cache["key"] == cache_key
            and len(_suggestions_cache["suggestions"]) > 0
            and (time.time() - _suggestions_cache["timestamp"]) < 600
        ):
            return {"suggestions": _suggestions_cache["suggestions"]}

        # If a non-refresh request arrives while generation is already in-flight for this key, await it
        if not refresh and cache_key in _suggestions_inflight:
            try:
                in_flight_res = await asyncio.shield(_suggestions_inflight[cache_key])
                return {"suggestions": in_flight_res}
            except Exception:  # noqa: BLE001, S110
                # If the in-flight task was cancelled or failed, fall through to fresh generation
                pass

        async def _generate_suggestions() -> list[str]:
            import json

            import openai

            client = openai.AsyncOpenAI(api_key=api_key)
            try:
                prompt = (
                    "The user previously researched these topics:\n"
                    + "\n".join(f"- {q}" for q in recent_queries)
                    + "\n\nSuggest 4 diverse, intriguing follow-up or adjacent research topics. "
                    "Return ONLY a JSON array of 4 strings, no markdown, no commentary."
                )
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                )
                content = response.choices[0].message.content or "[]"
                cleaned = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                parsed = json.loads(cleaned)
                if isinstance(parsed, list) and len(parsed) > 0:
                    return [str(p) for p in parsed[:4]]
            except Exception as err:  # noqa: BLE001
                print(f"Suggestions generation fallback note: {err}")
            return default_suggestions

        task = asyncio.create_task(_generate_suggestions())
        _suggestions_inflight[cache_key] = task
        try:
            generated = await task
            return {"suggestions": generated}
        finally:
            _suggestions_inflight.pop(cache_key, None)
    except Exception as e:  # noqa: BLE001
        print(f"Suggestions generation note: {e}")

    return {"suggestions": default_suggestions}


async def run_research_task(
    job_id: str,
    query: str,
    depth: int,
    breadth: int,
    session_id: str | None = None,
    client_ip: str | None = None,
) -> None:
    """Delegate research execution to the autonomous agent engine on Render."""
    register_active_workflow(job_id, session_id, client_ip)
    try:
        await dispatch_research_job(
            job_id=job_id,
            query=query,
            depth=depth,
            breadth=breadth,
            session_id=session_id,
            client_ip=client_ip,
        )
    finally:
        unregister_active_workflow(job_id, session_id, client_ip)


@app.get("/api/research", response_model=list[ResearchJobRead])
async def list_research_jobs(
    db: SessionDep,
    session_id: SessionIdDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List research jobs belonging exclusively to the current active session."""
    query = (
        select(ResearchJob)
        .where(ResearchJob.session_id == session_id)
        .order_by(desc(ResearchJob.created_at))
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    jobs = result.scalars().all()
    return [
        ResearchJobRead(
            id=job.id or "",
            query=job.query,
            depth=job.depth,
            breadth=job.breadth,
            status=job.status,
            result=job.result,
            created_at=job.created_at,
            logs=job.logs,
            is_owner=True,
        )
        for job in jobs
    ]


@app.post("/api/research", response_model=ResearchJobRead)
async def create_research_job(
    research_job_create: ResearchJobCreate,
    background_tasks: BackgroundTasks,
    db: SessionDep,
    session_id: SessionIdDep,
    client_ip: ClientIpDep,
):
    """Create and queue a new research job, enforcing concurrency and sliding-window rate limits."""
    query_text = research_job_create.query.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Research query cannot be empty")

    depth = max(1, min(5, research_job_create.depth))
    breadth = max(2, min(10, research_job_create.breadth))

    # Hold the lock through rate limit verification and job insertion to prevent races
    async with rate_limit_lock:
        await check_rate_limits(db, session_id=session_id, client_ip=client_ip)

        db_job = ResearchJob(
            id=str(uuid.uuid4()),
            query=query_text,
            depth=depth,
            breadth=breadth,
            status=JobStatus.QUEUED,
            logs_json="[]",
            session_id=session_id,
            client_ip=client_ip,
        )
        db.add(db_job)
        await record_research_usage(db, session_id=session_id, client_ip=client_ip)
        await db.commit()
        await db.refresh(db_job)

    job_id = db_job.id
    if job_id is None:
        raise HTTPException(status_code=500, detail="Failed to create job")

    background_tasks.add_task(
        run_research_task,
        job_id,
        db_job.query,
        db_job.depth,
        db_job.breadth,
        session_id,
        client_ip,
    )

    return ResearchJobRead(
        id=job_id,
        query=db_job.query,
        depth=db_job.depth,
        breadth=db_job.breadth,
        status=db_job.status,
        result=db_job.result,
        created_at=db_job.created_at,
        logs=db_job.logs,
        is_owner=True,
    )


@app.get("/api/research/{job_id}", response_model=ResearchJobRead)
async def get_research_job(
    job_id: str,
    db: SessionDep,
    session_id: SessionIdDep,
):
    """Retrieve research report. Shareable links allow reading by ID while reporting ownership."""
    result = await db.execute(select(ResearchJob).where(ResearchJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")

    result_job_id = job.id
    if result_job_id is None:
        raise HTTPException(status_code=500, detail="Invalid job state")

    return ResearchJobRead(
        id=result_job_id,
        query=job.query,
        depth=job.depth,
        breadth=job.breadth,
        status=job.status,
        result=job.result,
        created_at=job.created_at,
        logs=job.logs,
        is_owner=(job.session_id == session_id),
    )


@app.delete("/api/research/{job_id}")
async def delete_research_job(
    job_id: str,
    db: SessionDep,
    session_id: SessionIdDep,
):
    """Delete a research session, strictly rejecting deletions without verified matching ownership."""
    result = await db.execute(select(ResearchJob).where(ResearchJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")

    # Strict ownership check: prevent unowned reports or other sessions from deleting this research
    if not job.session_id or job.session_id != session_id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: You do not have permission to delete this research session.",
        )

    await db.delete(job)
    await db.commit()
    return {"status": "deleted", "id": job_id}


@app.post("/api/research/{job_id}/claim", response_model=ResearchJobRead)
async def claim_legacy_job(
    job_id: str,
    db: SessionDep,
    session_id: SessionIdDep,
):
    """Claim an unassigned legacy research report for the current session.

    Enables historical reports created prior to session isolation to be adopted
    and managed by the claiming session without exposing them globally.
    """
    result = await db.execute(select(ResearchJob).where(ResearchJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")

    if job.session_id and job.session_id != session_id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Report is already associated with another session.",
        )

    if not job.session_id:
        job.session_id = session_id
        await db.commit()
        await db.refresh(job)

    result_job_id = job.id
    if result_job_id is None:
        raise HTTPException(status_code=500, detail="Invalid job state")

    return ResearchJobRead(
        id=result_job_id,
        query=job.query,
        depth=job.depth,
        breadth=job.breadth,
        status=job.status,
        result=job.result,
        created_at=job.created_at,
        logs=job.logs,
        is_owner=True,
    )
