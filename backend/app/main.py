import asyncio
import os
import traceback
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlmodel import desc, select

from app.db import engine, get_session, init_db
from app.models import JobStatus, ResearchJob, ResearchJobCreate, ResearchJobRead
from app.services.research import ResearchWorkflow

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@asynccontextmanager
async def lifespan(app: FastAPI):
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
extra_origins = os.getenv("ALLOWED_ORIGINS", "")
if extra_origins:
    allowed_origins.extend([o.strip() for o in extra_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:[0-9]+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "service": "noesis",
        "timestamp": datetime.now(UTC).isoformat(),
    }


# In-memory cache for research suggestions
_suggestions_cache = {
    "key": "",
    "suggestions": [],
    "timestamp": 0.0,
}
_suggestions_inflight: dict[str, asyncio.Task] = {}


@app.get("/api/suggestions")
async def get_suggestions(
    db: SessionDep,
    refresh: bool = Query(default=False),
):
    """
    Generate dynamic research suggestions based on previous research topics
    using a fast, lightweight model (gpt-4o-mini). Cached by recent queries key.
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
            select(ResearchJob.query).order_by(desc(ResearchJob.created_at)).limit(6)
        )
        recent_queries = [r[0] for r in result.all() if r[0]]
        api_key = os.getenv("OPENAI_API_KEY")
        if not recent_queries or not api_key:
            return {"suggestions": default_suggestions}

        cache_key = "|".join(recent_queries[:5])
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
                    + "\n".join(f"- {q}" for q in recent_queries[:5])
                    + "\n\nSuggest 4 high-value follow-up or related research inquiry titles (max 8 words each). "
                    + 'Return ONLY a JSON array of strings, for example: ["Topic A", "Topic B", "Topic C", "Topic D"].'
                )
                response = await client.chat.completions.create(
                    model=os.getenv("QUERY_AGENT_MODEL", "gpt-4o-mini"),
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=150,
                )
                content = (response.choices[0].message.content or "").strip()
                clean = (
                    content.strip()
                    .removeprefix("```json")
                    .removeprefix("```")
                    .removesuffix("```")
                    .strip()
                )
                parsed = json.loads(clean)
                if isinstance(parsed, list):
                    # Accept only nonblank strings
                    valid_items = [
                        s.strip() for s in parsed if isinstance(s, str) and s.strip()
                    ]
                    if valid_items:
                        formatted = valid_items[:4]
                        _suggestions_cache["key"] = cache_key
                        _suggestions_cache["suggestions"] = formatted
                        _suggestions_cache["timestamp"] = time.time()
                        return formatted
                return default_suggestions
            finally:
                await client.close()

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


async def run_research_task(job_id: str, query: str, depth: int, breadth: int):
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        try:
            result = await db.execute(
                select(ResearchJob).where(ResearchJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            if not job:
                print(f"Job {job_id} not found")
                return

            job.status = JobStatus.RUNNING
            job.logs = [
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "message": "Research started",
                    "level": "info",
                }
            ]
            await db.commit()

            async def log_callback(log_entry: dict):
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
                            "message": "Research completed",
                            "level": "success",
                        }
                    )
                    job.logs = logs
                    await final_db.commit()

        except Exception as e:
            print(f"Error in research task: {e}")
            traceback.print_exc()
            async with session_factory() as err_db:
                result = await err_db.execute(
                    select(ResearchJob).where(ResearchJob.id == job_id)
                )
                job = result.scalar_one_or_none()
                if job:
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


@app.get("/api/research", response_model=list[ResearchJobRead])
async def list_research_jobs(
    db: SessionDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    query = (
        select(ResearchJob)
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
        )
        for job in jobs
    ]


@app.post("/api/research", response_model=ResearchJobRead)
async def create_research_job(
    research_job_create: ResearchJobCreate,
    background_tasks: BackgroundTasks,
    db: SessionDep,
):
    query_text = research_job_create.query.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Research query cannot be empty")

    depth = max(1, min(5, research_job_create.depth))
    breadth = max(2, min(10, research_job_create.breadth))

    db_job = ResearchJob(
        id=str(uuid.uuid4()),
        query=query_text,
        depth=depth,
        breadth=breadth,
        status=JobStatus.QUEUED,
        logs_json="[]",
    )
    db.add(db_job)
    await db.commit()
    await db.refresh(db_job)

    job_id = db_job.id
    if job_id is None:
        raise HTTPException(status_code=500, detail="Failed to create job")

    background_tasks.add_task(
        run_research_task, job_id, db_job.query, db_job.depth, db_job.breadth
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
    )


@app.get("/api/research/{job_id}", response_model=ResearchJobRead)
async def get_research_job(job_id: str, db: SessionDep):
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
    )


@app.delete("/api/research/{job_id}")
async def delete_research_job(job_id: str, db: SessionDep):
    result = await db.execute(select(ResearchJob).where(ResearchJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")

    await db.delete(job)
    await db.commit()
    return {"status": "deleted", "id": job_id}
