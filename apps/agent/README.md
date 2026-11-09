# Noesis Agent Engine

Autonomous multi-agent research execution and synthesis service designed for continuous container deployment on Render.

## Overview

The Agent Engine manages:
- **Multi-Agent Swarm**:
  - `QueryAgent`: Deconstructs research queries into orthogonal exploration vectors.
  - `SearchAgent`: Scrapes and extracts factual evidence via DuckDuckGo Search.
  - `FollowUpAgent`: Evaluates knowledge gaps and guides recursive search loops.
  - `SynthesisAgent`: Formulates executive briefs with citations and comparative tables.
- **Real-Time Log Streaming**: Streams structured reasoning steps and findings directly to Neon PostgreSQL.
- **Resilient Execution**:
  - HTTP webhook receiver at `/api/jobs/dispatch`.
  - Background queue consumer polling PostgreSQL for queued jobs.

## Local Development

```bash
cp .env.example .env
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

## Running Tests

```bash
uv run pytest
```
