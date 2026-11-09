import asyncio
import os
from typing import Any

import httpx


async def dispatch_research_job(
    job_id: str,
    query: str,
    depth: int,
    breadth: int,
    session_id: str | None = None,
    client_ip: str | None = None,
) -> bool:
    """Dispatch a research task to the autonomous agent engine on Render.

    If AGENT_SERVICE_URL is set (e.g. in production pointing to https://noesis-agent.onrender.com),
    sends an HTTP dispatch request with the internal service secret.
    If the agent service is cold-starting or temporarily unreachable, the job remains
    persisted in PostgreSQL with status 'QUEUED', where the agent's queue poller will
    automatically pick it up upon wake-up.

    Args:
        job_id: Unique research job identifier.
        query: Research query text.
        depth: Recursive search depth.
        breadth: Orthogonal queries breadth.
        session_id: Session identifier.
        client_ip: Client IP address.

    Returns:
        True if successfully delivered or queued, False if delivery had a transient note.
    """
    agent_url = os.getenv("AGENT_SERVICE_URL", "").strip().rstrip("/")
    secret = (
        os.getenv("AGENT_INTERNAL_SECRET", "").strip()
        or os.getenv("INTERNAL_SERVICE_KEY", "").strip()
    )

    if agent_url:
        try:
            headers = {}
            if secret:
                headers["X-Internal-Secret"] = secret

            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(
                    f"{agent_url}/api/jobs/dispatch",
                    json={
                        "job_id": job_id,
                        "query": query,
                        "depth": depth,
                        "breadth": breadth,
                        "session_id": session_id,
                        "client_ip": client_ip,
                    },
                    headers=headers,
                )
                if res.status_code in (200, 202):
                    return True
                print(
                    f"[Dispatcher] Agent service returned {res.status_code}: {res.text}. "
                    "Job remains QUEUED in database for worker pickup."
                )
                return False
        except Exception as e:
            # Render cold start or network delay: job is safely QUEUED in Neon PostgreSQL
            print(
                f"[Dispatcher] Note: Agent dispatch webhook did not acknowledge ({e}). "
                "Job remains safely QUEUED in PostgreSQL; worker will process once awake."
            )
            return False

    # In local development or testing when AGENT_SERVICE_URL is not set:
    # If in-process execution is explicitly enabled or in test mode:
    run_in_process = os.getenv("RUN_IN_PROCESS", "false").lower() in ("true", "1")
    if run_in_process:
        try:
            # Optional local-only fallback if agent package is available in the environment
            from app.services.research import ResearchWorkflow  # type: ignore
            # Local in-process fallback
            async def _local_runner():
                try:
                    wf = ResearchWorkflow(query=query, log_callback=None, depth=depth, breadth=breadth)
                    await wf.research()
                except Exception as err:
                    print(f"[Local Runner Error]: {err}")

            asyncio.create_task(_local_runner())
            return True
        except ImportError:
            pass

    return True
