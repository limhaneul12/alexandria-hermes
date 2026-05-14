# ALEXANDRIA-HERMES

> Library-style skill and prompt archive for humans, AI agents, and optional librarian agents.

<p align="center">
  <img src="./docs/assets/alexandria-hermes-cover.png" alt="ALEXANDRIA-HERMES archive cover" width="100%" />
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img alt="Python" src="https://img.shields.io/badge/python-3.13%20%7C%203.14-3776AB?logo=python&logoColor=white"></a>
  <a href="https://docs.astral.sh/uv/"><img alt="uv" src="https://img.shields.io/badge/uv-0.8.4-654FF0?logo=astral&logoColor=white"></a>
  <a href="https://fastapi.tiangolo.com/"><img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.136.1-009688?logo=fastapi&logoColor=white"></a>
  <a href="https://www.sqlalchemy.org/"><img alt="SQLAlchemy" src="https://img.shields.io/badge/SQLAlchemy-2.0.49-D71F00"></a>
  <a href="https://nextjs.org/"><img alt="Next.js" src="https://img.shields.io/badge/Next.js-15-black?logo=nextdotjs"></a>
  <a href="https://react.dev/"><img alt="React" src="https://img.shields.io/badge/React-19-149ECA?logo=react&logoColor=white"></a>
  <img alt="Backend tests" src="https://img.shields.io/badge/backend_tests-164%20passed-brightgreen">
  <img alt="Coverage" src="https://img.shields.io/badge/coverage-pytest%20suite-lightgrey">
</p>

---

## What is Alexandria-Hermes?

ALEXANDRIA-HERMES is a digital archive for reusable AI-agent resources.

The product goal is simple: manage **skills** and **prompts** like a library so people, agents, and optional librarian agents can find, register, classify, use, and revisit them later.

Hermes is not the library itself. Hermes, humans, and other agents can all use the platform:

- humans can directly create folders, skills, and prompts
- agents can register or retrieve reusable resources
- an optional librarian agent can help classify, recommend, and import resources
- MINIO can hold original files while Hermes stores searchable metadata and placement

The current implementation focuses on:

- skill and prompt archive management
- folder/category organization
- usage history and recently accessed resources
- optional OpenAI-backed librarian provider registration
- optional MINIO scan/import for existing external archives
- CLI access for humans and agents
- a Next.js document-style library UI

The cover art represents the long-term archive direction. The current MVP is focused on **Skills** and **Prompts** first; MCP and workflow shelves are planned expansion areas.

---

## Concept Art

<p align="center">
  <img src="./docs/assets/alexandria-hermes-library.png" alt="ALEXANDRIA-HERMES library concept art" width="100%" />
</p>

The project uses archive imagery to communicate the product direction: skills and prompts first, with MCP and workflow shelves expanding as the platform matures.

---

## Tech Stack

### Backend

| Area | Technology |
| --- | --- |
| Runtime | Python `>=3.13,<3.15` |
| Package manager | uv `0.8.4` |
| Web framework | FastAPI `0.136.1` |
| Data validation | Pydantic `2.13.4` |
| Database layer | SQLAlchemy `2.0.49` + Alembic |
| Local DB | SQLite / aiosqlite |
| Provider SDK | OpenAI Python SDK `2.36.0` |
| Object storage | MINIO Python SDK `7.2.20` |
| Quality gates | Ruff, Pyrefly, Pytest |

### Frontend

| Area | Technology |
| --- | --- |
| Framework | Next.js `15` |
| UI runtime | React `19` |
| Language | TypeScript |
| Data fetching | TanStack Query |
| State | Zustand |
| Charts/icons | Recharts, Lucide React |

---

## Current Status

This repository is an active MVP, not a finished product.

Working surfaces include:

- FastAPI backend with archive, category, provider, prompt, skill, and MINIO routes
- SQLite-backed local development storage
- Next.js frontend for dashboard, explore/library, details, settings, providers, and imports
- CLI entrypoints:
  - `alexandria-hermes`
  - `alex-hermes`
- backend quality gate with `164` passing tests

Planned/expanding areas:

- richer librarian classification
- prompt preview/linting depth
- MCP resource expansion
- stronger import review workflows
- real deployment/auth hardening

---

## Validation Snapshot

Latest local validation run:

```bash
cd backend
make ci
```

Result:

```text
ruff format --check: 182 files already formatted
ruff check: All checks passed
pyrefly check: 0 errors
shared guardrails: 25 passed
backend tests: 164 passed
```

Frontend validation:

```bash
cd frontend
npm run lint
npm run test:ui-contract
npm run build
npm run security:npm-supply-chain
```

Notes:

- `coverage.py` is not wired into the repo yet, so the README reports the current pytest suite result rather than a percentage badge.
- NPM supply-chain hold is active in this repo. Do **not** run `npm install`, `npm uninstall`, or `npx` unless the hold is explicitly lifted.

---

## Quick Start

### Backend

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health checks:

- Live: `http://localhost:8000/health/live`
- Ready: `http://localhost:8000/health/ready`

### Frontend

Use the existing lockfile/dependencies. Do not install new packages during the npm hold.

```bash
cd frontend
npm run security:npm-supply-chain
npm run dev
```

Frontend runs at:

- `http://localhost:3000`

### Full Stack

```bash
docker compose up --build
```

This starts:

- backend: `http://localhost:8000`
- frontend: `http://localhost:3000`

---

## CLI

The CLI is a thin client over the backend HTTP API. It does not bypass backend permissions, validation, duplicate handling, or MINIO safety rules.

Install once for normal shell usage:

```bash
cd backend
uv sync
cd ..
./scripts/install-cli.sh
```

Then use it without `uv run`:

```bash
alexandria-hermes health
alexandria-hermes folders list --tree
alexandria-hermes folders create --name Backend
alexandria-hermes folders delete <folder-id>
alexandria-hermes library list --type SKILL --folder-id <folder-id>
alexandria-hermes library search "dependency injection"
alexandria-hermes skills list --limit 20
alexandria-hermes skills get <skill-id> --json
alexandria-hermes skills delete <skill-id>
alexandria-hermes skills create \
  --title "FastAPI Dependency Injection" \
  --purpose "Teach agents dependency patterns" \
  --content-file ./skill.md \
  --tag fastapi \
  --tool pytest \
  --active
alexandria-hermes minio scan --limit 24 --json
alexandria-hermes minio import --limit 48
```

Short alias:

```bash
alex-hermes health
```

Configuration:

- default API URL: `http://localhost:8000`
- override with env: `HERMES_API_URL=http://localhost:8000`
- override per command: `--base-url http://localhost:8000`
- use `--json` for agent automation
- without installation, repo-local execution is available via `./bin/alexandria-hermes ...`

---

## OpenAI and MINIO Providers

### OpenAI

Hermes uses the official OpenAI Python SDK and API-key authentication for the librarian provider path.

Current position:

- supported: OpenAI API key
- not productized: ChatGPT/Codex OAuth proxy packages
- reason: official OpenAI API usage is API-key based; OAuth is a different flow for actions/connectors or external-service login scenarios

### MINIO

MINIO is optional. It is intended for teams that already keep skills/prompts as files in object storage.

Recommended model:

- MINIO keeps originals
- Hermes DB stores searchable metadata, classification, folder placement, and object location
- users can scan candidates before importing
- imports should be reviewable and idempotent

MINIO is not required for local development.

---

## Project Layout

```text
backend/
  app/
    main.py                  # FastAPI app entrypoint
    cli.py                   # CLI entrypoint
    library/                 # archive domain/application/interface/infrastructure
    platform/                # config, lifecycle, logging, middleware, storage
    shared/                  # guardrails, exceptions, serialization, utilities
  migrations/                # Alembic migrations
  tests/                     # pytest suite
  pyproject.toml

frontend/
  src/
    app/                     # Next.js app routes
    components/              # layout, library, dashboard, settings, ui
    lib/                     # API clients, backend adapters, i18n, form helpers
    store/                   # Zustand store
    types/                   # shared DTO types
  scripts/                   # UI contract and security checks

scripts/
  install-cli.sh

docs/
  librain/                   # implementation plans and library/librarian notes
  prompting_lib/             # prompt-library implementation plans
```

---

## Development Commands

### Backend

```bash
cd backend
uv sync
uv run ruff format --check .
uv run ruff check .
uv run pyrefly check
uv run pytest -q
make ci
```

### Frontend

```bash
cd frontend
npm run security:npm-supply-chain
npm run lint
npm run test:ui-contract
npm run build
npm run dev
```

---

## Configuration

Backend config is environment-based.

Common local values:

```bash
SERVICE_ENV=local
SERVICE_NAME=alexandria-hermes
```

Provider credentials should stay in local environment/config paths only. Do not commit secrets.

---

## Product Philosophy

> Knowledge should not only be stored.  
> It should remain findable, reusable, attributable, and usable by agents at the right moment.

ALEXANDRIA-HERMES aims to become an operational archive where:

- skills are reusable capabilities
- prompts are reusable instruction artifacts
- folders behave like shelves
- usage history helps retrieval
- librarian agents are optional helpers, not hard dependencies
- humans and agents can both participate

