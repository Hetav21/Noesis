from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlmodel import select
from typing import List
import uuid
import asyncio
from datetime import datetime

from app.db import init_db, get_session, engine
from app.models import ResearchJob, ResearchJobCreate, ResearchJobRead, JobStatus
from app.services.research import ResearchWorkflow

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    await init_db()


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
                    "timestamp": datetime.utcnow().isoformat(),
                    "message": "Research started",
                    "level": "info",
                }
            ]
            await db.commit()

            async def log_callback(log_entry: dict):
                result = await db.execute(
                    select(ResearchJob).where(ResearchJob.id == job_id)
                )
                job = result.scalar_one_or_none()
                if job:
                    logs = job.logs
                    log_entry["timestamp"] = datetime.utcnow().isoformat()
                    logs.append(log_entry)
                    job.logs = logs
                    await db.commit()

            workflow = ResearchWorkflow(
                query=query, log_callback=log_callback, depth=depth, breadth=breadth
            )
            final_result = await workflow.research()

            result = await db.execute(
                select(ResearchJob).where(ResearchJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            if job:
                job.status = JobStatus.COMPLETED
                job.result = final_result
                logs = job.logs
                logs.append(
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "message": "Research completed",
                        "level": "success",
                    }
                )
                job.logs = logs
                await db.commit()

        except Exception as e:
            print(f"Error in research task: {e}")
            import traceback

            traceback.print_exc()
            result = await db.execute(
                select(ResearchJob).where(ResearchJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            if job:
                job.status = JobStatus.FAILED
                job.result = f"Error: {str(e)}"
                await db.commit()


@app.post("/api/research", response_model=ResearchJobRead)
async def create_research_job(
    research_job_create: ResearchJobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
):
    db_job = ResearchJob(
        id=str(uuid.uuid4()),
        query=research_job_create.query,
        depth=research_job_create.depth,
        breadth=research_job_create.breadth,
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
async def get_research_job(job_id: str, db: AsyncSession = Depends(get_session)):
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
