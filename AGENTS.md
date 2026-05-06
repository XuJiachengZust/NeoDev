# Repository Guidelines
遵循harness规则
## Project Structure & Module Organization
Core code lives in `src/`. `src/service/` contains the FastAPI app, routers, repositories, services, storage, and workflows. `src/deepagents/` holds agent graph, middleware, and backend adapters. `src/gitnexus_parser/` contains parsing and graph-ingestion logic. Deployment assets live in `docker/`, while root files such as `.env.example`, `docker-compose.yml`, `environment.yml`, `Dockerfile`, and `pytest.ini` define runtime behavior.

## Build, Test, and Development Commands
- `conda env create -f environment.yml`: create the Python environment.
- `conda activate NeoDev`: activate local development.
- `PYTHONPATH=src python -m uvicorn service.main:app --reload`: run the API locally.
- `pytest`: run backend tests when `tests/` exists.
- `docker compose up -d --build`: start the Docker stack.

Read `harness/BOOTSTRAP.md` before non-trivial work and load only the relevant harness files.

## Coding Style & Naming Conventions
Use 4-space indentation in Python. Keep modules, functions, and variables in `snake_case`; classes in `PascalCase`. Preserve the current layering: routers handle transport, services hold business logic, repositories handle persistence, and shared behavior belongs in focused helpers instead of mixed large modules.

## Testing Guidelines
Use `pytest` for backend verification. Add tests under `tests/` with names like `test_service_api.py` or `test_branch_service.py`. Favor targeted coverage for changed routers, services, repositories, and workflow behavior. Do not claim completion from static review alone when the change can be executed locally or in Docker.

## Commit & Pull Request Guidelines
Follow Conventional Commit prefixes already used in history: `feat:`, `fix:`, `test:`, `docs:`, `chore:`. Keep subjects short and specific. PRs should summarize affected areas, list validation performed, call out config changes, and include request/response examples when API behavior changes.

## Security & Configuration Tips
Do not commit real secrets. Treat `.env` as local-only. Use `.env.example` and `src/config.example.json` as the public reference for configuration shape. Keep remote server and deployment details in `harness/context/dev-environment.md`, not in scattered notes.
