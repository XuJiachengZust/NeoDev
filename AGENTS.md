# Repository Guidelines

## Project Structure & Module Organization
`src/service` contains the FastAPI backend, including `routers/`, `repositories/`, and workflow helpers. `src/gitnexus_parser` and `src/deepagents` hold parsing and agent-related logic. `tests/` mirrors backend features with pytest files such as `test_api_projects.py`. The frontend lives in `web/src` with `components/`, `pages/`, `hooks/`, and `api/`. Deployment assets are under `docker/`, while design notes and backend TODOs live in `docs/`.

## Build, Test, and Development Commands
Create the Python environment with `conda env create -f environment.yml` and activate `neodev`. Run the API from the repo root with `PYTHONPATH=src python -m uvicorn service.main:app --reload` or `uvicorn service.main:app --reload`. Run backend tests with `pytest` and target a file with `pytest tests/test_service_api.py`. In `web/`, use `npm install`, `npm run dev`, `npm run build`, and `npm run test:run`. For the full stack, use `docker compose up -d --build`.

## Coding Style & Naming Conventions
Follow existing style instead of introducing a new one. Python uses 4-space indentation, snake_case modules, and typed or descriptive helper names. TypeScript/React uses 2-space indentation, PascalCase component files such as `ProductDashboardPage.tsx`, and camelCase hooks and utilities such as `useProductContext.ts`. Keep routers, repositories, and pages focused on one responsibility. No dedicated lint config is checked in, so keep changes small, readable, and consistent with neighboring files.

## Testing Guidelines
Backend tests use `pytest` with `pythonpath = src` from `pytest.ini`. Name tests `test_*.py` and keep API coverage near the corresponding router or repository behavior. Frontend tests use `vitest` with Testing Library; colocate them as `*.test.tsx` or `*.test.ts`. Add or update tests for new routes, repository behavior, parsing logic, and UI state transitions.

## Commit & Pull Request Guidelines
Recent history uses short Conventional Commit prefixes such as `feat:`. Continue with `feat:`, `fix:`, `refactor:`, or `test:` followed by a concise summary. Pull requests should state the scope, list affected areas (`src/service`, `web/src`, `docker/`), mention config changes, and include screenshots for UI updates. Link related issues or requirements when available.

## Security & Configuration Tips
Start from `.env.example`; do not commit real secrets. Review settings for `OPENAI_API_KEY`, `NEO4J_*`, `POSTGRES_*`, and storage paths before running Docker or migrations. Avoid committing generated output from `web/dist` unless the release process explicitly requires it.

## Codex Harness Usage
Before executing non-trivial tasks, read `codex-harness/BOOTSTRAP.md` and then `codex-harness/system/master-prompt.md`. Load only the task-relevant files under `codex-harness/rules/` rather than the entire harness.

Treat `codex-harness` as a development governance layer for agent behavior, not as NeoDev product runtime. If harness guidance conflicts with this `AGENTS.md`, follow `AGENTS.md` first.
