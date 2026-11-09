# Noesis REST API Gateway

FastAPI service designed for serverless deployment on Vercel (`api.noesis.hetav.dev`).

## Overview

The API gateway handles:
- **Client Session Isolation**: HMAC server-signed session cookies and ownership verification.
- **Durable Rate Limiting**: Sliding-window hourly quotas and active concurrency enforcement.
- **Research Job Lifecycle**: CRUD operations, shareable read links, and legacy report adoption.
- **Query Suggestions**: Dynamic, session-scoped research topic suggestions powered by OpenAI.
- **Agent Dispatching**: Dispatches research execution to the autonomous agent engine on Render via `POST /api/jobs/dispatch`.

## Local Development

```bash
cp .env.example .env
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Running Tests

```bash
uv run pytest
```
