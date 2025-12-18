# AGENTS.md

## Commands
- **Backend**: `cd backend && uv run uvicorn app.main:app --reload` (port 8000)
- **Frontend**: `cd frontend && bun dev` (port 5173)
- **Frontend build**: `cd frontend && bun run build` (runs tsc + vite)
- **Frontend lint**: `cd frontend && bun run lint`
- **Kill ports**: `kill -9 $(lsof -ti:8000,5173)` or use `ss -tlnp | grep :PORT`

## Code Style
- **Python**: Python 3.14+, async/await, Pydantic models, SQLModel for DB, type hints required
- **TypeScript**: Strict mode, `verbatimModuleSyntax` (use `import type` for types)
- **Frontend**: React 19 + React Router 7 + Tailwind CSS 4, functional components only
- **Imports**: Group stdlib, third-party, local. Use `from x import y` in Python
- **Naming**: snake_case (Python), camelCase (TS), PascalCase (components/classes)
- **Error handling**: Never use empty catch blocks, never use `as any` or `@ts-ignore`

## Architecture
- Backend: FastAPI + SQLite (async via aiosqlite) + OpenAI Agents SDK
- Frontend: Vite + React + react-router with `createBrowserRouter`
- API: REST at `/api/research` (POST create, GET by ID), polling for status updates
- Light theme UI (bg-gray-50, text-gray-900), no dark mode
