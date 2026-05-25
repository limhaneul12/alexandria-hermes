# Repository Guidelines

## Project Structure & Module Organization
This repo is now a backend/CLI service for Alexandria-Hermes:
- `backend/` Python FastAPI service and CLI/MCP integration
  - `backend/AGENTS.md` and `backend/.agents/rule/**` are mandatory backend development rules. Read them before modifying backend code.
  - `backend/app/` application code (entrypoint: `backend/app/main.py`)
  - `backend/app/platform/` platform logic (routing, middleware, lifecycle, config, logging)
  - `backend/app/shared/` reusable helpers and guardrails
  - `backend/tests/` backend tests (`test_*.py`)
- `docker-compose.yml` for the backend service only
- `README.md` for high-level startup notes

The previous Next.js `frontend/` service has been removed. Do not add npm/Next.js workflows unless the product direction changes explicitly.

## Build, Test, and Development Commands
### Backend (Python)
Before backend code changes, read `backend/AGENTS.md` and the referenced `backend/.agents/rule/**` documents first.
```bash
cd backend
uv sync
uv run ruff check .        # lint
uv run ruff format .       # format
uv run pyrefly check       # type/safety check
uv run pytest -q          # run backend tests
```

### Service
```bash
docker compose up --build
```
Starts the backend on `127.0.0.1:8000`.

## Coding Style & Naming Conventions
- Python: target `3.13` (`pyproject.toml`) with `ruff` formatting rules.
  - 88-char line length, 4-space indentation, double quotes.
  - Prefer explicit module paths (`app.platform...`), Pydantic models, and typed public functions.
  - Docstrings should use `Args:` / `Return:` sections.
- Naming:
  - Python: `snake_case` for functions/variables, `PascalCase` for classes.
  - Paths/files should reflect domain (`platform`, `shared`, `schemas`, `util`, `middleware`).

## Testing Guidelines
- Backend test framework: `pytest`.
- Tests are discovered under `backend/tests/` and named `test_*.py`.
- Run `uv run pytest -q` before review.
- Keep tests fast and deterministic; avoid external service dependencies in default suite.

## Commit & Pull Request Guidelines
- Use the Lore commit protocol from the root runtime instructions when committing.
- PRs should include:
  - concise summary + impacted areas
  - validation run command outputs
  - risk/rollback notes when touching lifecycle, config, or logging behavior

## Security & Configuration Tips
- Runtime config is environment-based (`.env`, `SERVICE_` prefix for app config, `STREAM_` for stream config).
- Avoid committing secrets; keep local credentials in local env files only.
- For local health checks, keep backend exposed only as needed and verify startup endpoints via:
  - `http://localhost:8000/health/live`
