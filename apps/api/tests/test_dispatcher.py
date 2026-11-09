from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.dispatcher import (
    cancel_remote_job,
    dispatch_research_job,
    is_dispatch_configured,
)


@pytest.mark.asyncio
async def test_dispatch_fallback_when_testing_or_queue_only(monkeypatch):
    """When AGENT_SERVICE_URL is unset but in test mode, dispatcher returns True."""
    monkeypatch.delenv("AGENT_SERVICE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    success = await dispatch_research_job(
        job_id="test-job-1",
        query="Quantum gravity",
        depth=1,
        breadth=2,
    )
    assert success is True


def test_is_dispatch_configured(monkeypatch):
    """Verify is_dispatch_configured logic across env states."""
    monkeypatch.delenv("AGENT_SERVICE_URL", raising=False)
    monkeypatch.delenv("ALLOW_QUEUE_ONLY", raising=False)
    monkeypatch.delenv("TESTING", raising=False)
    assert is_dispatch_configured() is False

    monkeypatch.setenv("ALLOW_QUEUE_ONLY", "true")
    assert is_dispatch_configured() is True

    monkeypatch.delenv("ALLOW_QUEUE_ONLY", raising=False)
    monkeypatch.setenv("AGENT_SERVICE_URL", "https://agent.example.com")
    assert is_dispatch_configured() is True


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


@pytest.mark.asyncio
async def test_cancel_remote_job(monkeypatch):
    """When AGENT_SERVICE_URL is configured, cancel_remote_job posts json payload to /api/jobs/cancel."""
    monkeypatch.setenv("AGENT_SERVICE_URL", "https://agent.test.local")
    monkeypatch.setenv("AGENT_INTERNAL_SECRET", "test-secret-token")

    mock_response = httpx.Response(
        status_code=200,
        json={"status": "cancelled", "job_id": "job-cancel-123"},
        request=httpx.Request("POST", "https://agent.test.local/api/jobs/cancel"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        success = await cancel_remote_job("job-cancel-123")
        assert success is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"] == {"job_id": "job-cancel-123"}
        assert call_kwargs["headers"]["X-Internal-Secret"] == "test-secret-token"


@pytest.mark.asyncio
async def test_cancel_remote_job_unconfigured(monkeypatch):
    """When AGENT_SERVICE_URL is unset, cancel_remote_job returns False immediately without request."""
    monkeypatch.delenv("AGENT_SERVICE_URL", raising=False)
    success = await cancel_remote_job("job-cancel-456")
    assert success is False

