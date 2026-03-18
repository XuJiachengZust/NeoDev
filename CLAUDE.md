# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NeoDev is a code analysis and project management platform with three subsystems:
- **Service** (`src/service/`) — FastAPI REST API for project/version/commit/requirement management, impact analysis, and AI preprocessing. Uses PostgreSQL + pgvector.
- **GitNexus Parser** (`src/gitnexus_parser/`) — Multi-language code parser (Python, Java, Lua) using Tree-sitter. Builds an in-memory knowledge graph (nodes + relationships) and optionally writes to Neo4j.
- **Deep Agents** (`src/deepagents/`) — LangChain/LangGraph-based agent framework with composable middleware, pluggable backends, and sub-agent support.
- **Web Frontend** (`web/`) — React 18 + TypeScript + Vite dashboard for project onboarding, version management, commit tracking, requirement binding, and impact analysis visualization.

## Common Commands

### Backend (Python)
```bash
# Start API server (from repo root)
PYTHONPATH=src uvicorn service.main:app --reload

# Run all tests
pytest

# Run a single test file
pytest tests/test_service_api.py

# Run a single test function
pytest tests/test_service_api.py::test_function_name -v
```

### Frontend (web/)
```bash
cd web
npm install
npm run dev        # Dev server at localhost:5173, proxies /api to localhost:8000
npm run build      # Production build (tsc + vite)
npm run test       # Vitest in watch mode
npm run test:run   # Vitest single run
```

### Database
```bash
docker compose up -d    # Start PostgreSQL + pgvector (localhost:5432, user/pass: postgres/postgres, db: neodev)
docker compose down     # Stop
docker compose down -v  # Stop and delete data volumes
```

## Architecture

### Data Flow
```
Web (React, :5173) → /api proxy → FastAPI (:8000) → PostgreSQL (pgvector)
                                       ↕
                              GitNexus Parser → Neo4j (optional)
                              Deep Agents → LLM APIs (OpenAI-compatible)
```

### Service Layer Pattern
- **Routers** (`src/service/routers/`) — One file per domain: `projects.py`, `versions.py`, `commits.py`, `requirements.py`, `impact.py`, `preprocess.py`, `sync.py`, `parse.py`. Aggregated in `api.py` under `/api` prefix.
- **Repositories** (`src/service/repositories/`) — Data access using raw psycopg2 with `RealDictCursor`. No ORM.
- **Dependencies** (`src/service/dependencies.py`) — FastAPI `Depends()` for DB connections.
- **Security** — `path_allowlist.py` validates repo paths; `git_ops.py` provides read-only Git operations.

### GitNexus Parser Pipeline
`ingestion/pipeline.py` orchestrates: file walker → tree-sitter parser → symbol table → import resolver → call resolver. Graph types defined in `graph/types.py`, in-memory graph in `graph/graph.py`, Neo4j export in `neo4j_writer.py`.

### Deep Agents
`graph.py` exposes `create_deep_agent()` using LangGraph. Backends (`backends/protocol.py`) define a `BackendProtocol` for file storage. Middleware (`middleware/`) is composable (summarization, filesystem, sub-agents).

## Configuration

- `.env` at repo root — `OPENAI_API_KEY`, `OPENAI_BASE`, `OPENAI_MODEL_CHAT`, `AI_ANALYSIS_MAX_WORKERS`, optional `NEO4J_*` and `REPO_CLONE_BASE`.
- `src/config.example.json` — Neo4j connection defaults.
- Python 3.11 via Conda (`conda env create -f environment.yml`, activate `neodev`).
- Dependencies: `pip install -r src/requirements.txt`.

## Testing

- `pytest.ini` sets `pythonpath = src` and `testpaths = tests`.
- Tests requiring PostgreSQL auto-skip if DB is unavailable.
- `conftest.py` provides `db_connection`, `pg_conn`, and `client_with_db` (TestClient with DB override) fixtures. Migrations auto-apply from `docker/migrations/`.
- `TEST_DATABASE_URL` env var overrides the default connection string.

## Key Conventions

- Primary language for code comments and documentation is Chinese.
- Frontend dark theme with cyan (`#00F0FF`) primary accent, purple (`#B026FF`) AI accent.
- Frontend fonts: Inter (sans-serif), JetBrains Mono (monospace).
- No ORM — all SQL is hand-written in repository files.
- API routes return Pydantic-validated JSON; errors use `{"detail": ...}` format.
- Database migrations are ordered SQL files in `docker/migrations/`, auto-applied on first DB startup and in test fixtures.
