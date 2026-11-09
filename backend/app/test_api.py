import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db import init_db

@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "deep-research-agent"

from unittest.mock import patch

@pytest.mark.asyncio
async def test_research_job_lifecycle():
    await init_db()
    transport = ASGITransport(app=app)
    with patch("app.main.run_research_task"):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Create a job
            create_res = await client.post(
                "/api/research",
                json={"query": "Test quantum mechanics", "depth": 1, "breadth": 2},
            )
            assert create_res.status_code == 200
            job = create_res.json()
            job_id = job["id"]
            assert job_id is not None
            assert job["query"] == "Test quantum mechanics"
            assert job["depth"] == 1
            assert job["breadth"] == 2
            assert job["status"] in ["queued", "running"]

            # 2. Get the job by id
            get_res = await client.get(f"/api/research/{job_id}")
            assert get_res.status_code == 200
            fetched = get_res.json()
            assert fetched["id"] == job_id
            assert fetched["query"] == "Test quantum mechanics"

            # 3. List jobs
            list_res = await client.get("/api/research?limit=10")
            assert list_res.status_code == 200
            jobs_list = list_res.json()
            assert isinstance(jobs_list, list)
            assert any(j["id"] == job_id for j in jobs_list)

            # 4. Delete the job
            del_res = await client.delete(f"/api/research/{job_id}")
            assert del_res.status_code == 200
            assert del_res.json()["status"] == "deleted"

            # 5. Verify 404 after deletion
            not_found_res = await client.get(f"/api/research/{job_id}")
            assert not_found_res.status_code == 404

@pytest.mark.asyncio
async def test_validation_empty_query():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/research",
            json={"query": "   ", "depth": 2, "breadth": 4},
        )
        assert res.status_code == 400


@pytest.mark.asyncio
async def test_suggestions_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/suggestions")
        assert res.status_code == 200
        data = res.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
        assert len(data["suggestions"]) > 0
