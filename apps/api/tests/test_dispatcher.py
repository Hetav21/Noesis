import os
from unittest.mock import AsyncMock, patch

import pytest
import httpx

from app.dispatcher import dispatch_research_job


@pytest.mark.asyncio
async def test_dispatch_fallback_when_no_agent_url(monkeypatch):
    """When AGENT_SERVICE_URL is unset, dispatcher returns True cleanly without error."""
    monkeypatch.delenv("AGENT_SERVICE_URL", raising=False)
    success = await dispatch_research_job(
        job_id="test-job-1",
        query="Quantum gravity",
        depth=1,
        breadth=2,
    )
    assert success is True


@pytest.mark.asyncio
async def test_dispatch_calls_agent_service(monkeypatch):
    """When AGENT_SERVICE_URL is configured, dispatcher posts to /api/jobs/dispatch."""
    monkeypatch.setenv("AGENT_SERVICE_URL", "https://agent.test.local")
    monkeypatch.setenv("AGENT_INTERNAL_SECRET", "test-secret-token")

    mock_response = httpx.Response(
        status_code=202,
        json={"status": "accepted", "job_id": "test-job-2"},
        request=httpx.Request("POST", "https://agent.test.local/api/jobs/dispatch"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        success = await dispatch_research_job(
            job_id="test-job-2",
            query="Nuclear fusion commercialization",
            depth=2,
            breadth=4,
            session_id="session-xyz",
            client_ip="192.0.2.1",
        )

        assert success is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"]["job_id"] == "test-job-2"
        assert call_kwargs["json"]["query"] == "Nuclear fusion commercialization"
        assert call_kwargs["headers"]["X-Internal-Secret"] == "test-secret-token"


@pytest.mark.asyncio
async def test_dispatch_handles_render_cold_start_gracefully(monkeypatch):
    """If agent endpoint times out (cold start), dispatcher returns False but logs cleanly without crashing."""
    monkeypatch.setenv("AGENT_SERVICE_URL", "https://agent.test.local")
    monkeypatch.setenv("AGENT_INTERNAL_SECRET", "test-secret-token")

    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectTimeout("Connection timed out")):
        success = await dispatch_research_job(
            job_id="test-job-3",
            query="Carbon sequestration",
            depth=1,
            breadth=2,
        )
        # Should not throw, returns False so caller knows delivery was queued in DB
        assert success is False
