# ALEXANDRIA-HERMES

> Library-style archive and Context Vault for humans, AI agents, and optional librarian agents.

<p align="center">
  <img src="./docs/assets/alexandria-hermes-cover.png" alt="ALEXANDRIA-HERMES archive cover" width="100%" />
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img alt="Python" src="https://img.shields.io/badge/python-3.13%20%7C%203.14-3776AB?logo=python&logoColor=white"></a>
  <a href="https://docs.astral.sh/uv/"><img alt="uv" src="https://img.shields.io/badge/uv-0.8.4-654FF0?logo=astral&logoColor=white"></a>
  <a href="https://fastapi.tiangolo.com/"><img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.136.1-009688?logo=fastapi&logoColor=white"></a>
  <a href="https://docs.pydantic.dev/"><img alt="Pydantic" src="https://img.shields.io/badge/Pydantic-2.13.4-E92063?logo=pydantic&logoColor=white"></a>
  <a href="https://www.sqlalchemy.org/"><img alt="SQLAlchemy" src="https://img.shields.io/badge/SQLAlchemy-2.0.49-D71F00"></a>
  <a href="https://modelcontextprotocol.io/"><img alt="MCP" src="https://img.shields.io/badge/MCP-1.27.1-5B5BD6"></a>
  <a href="https://typer.tiangolo.com/"><img alt="Typer" src="https://img.shields.io/badge/Typer-0.25.1-009688"></a>
  <a href="https://www.python-httpx.org/"><img alt="HTTPX" src="https://img.shields.io/badge/HTTPX-0.28.1-0A7EA4"></a>
  <a href="https://nextjs.org/"><img alt="Next.js" src="https://img.shields.io/badge/Next.js-15.5.18-black?logo=nextdotjs"></a>
  <a href="https://react.dev/"><img alt="React" src="https://img.shields.io/badge/React-19.2.6-149ECA?logo=react&logoColor=white"></a>
  <img alt="Backend tests" src="https://img.shields.io/badge/backend_tests-191%20passed-brightgreen">
  <img alt="Typecheck" src="https://img.shields.io/badge/pyrefly-0%20errors-brightgreen">
</p>

---

## What is Alexandria-Hermes?

ALEXANDRIA-HERMES is a digital archive and context memory layer for reusable AI-agent resources.

The product goal is simple: manage **skills**, **prompts**, and **agent working context** like a library so humans, agents, and optional librarian agents can find, register, classify, recall, and reuse them later.

Hermes is not the library itself. Hermes, humans, and other agents can all use the platform:

- humans can directly create folders, skills, prompts, and captured context entries
- agents can register, retrieve, and recall reusable resources through HTTP, CLI, or MCP
- an optional librarian agent can help classify, recommend, and import resources
- MINIO can hold original files while Hermes stores searchable metadata and placement
- Context Vault can preserve handoffs, compact summaries, and RAG-ready chunks for later recall

The current implementation focuses on:

- skill and prompt archive management
- folder/category organization and usage history
- Context Vault linting, saving, chunking, recall, archive, and RAG health checks
- hybrid Context Pack retrieval with FTS plus optional vector/embedding support
- capture-review, context-vault, context-detail, and RAG-inspector UI surfaces
- optional OpenAI API-key and ChatGPT/Codex OAuth librarian provider registration
- optional MINIO scan/import for existing external archives
- native Typer CLI access for humans and agents
- MCP server access for agent/tool clients
- typed FastAPI/Pydantic contracts backed by SQLite, SQLAlchemy, and Alembic
- a Next.js document-style library UI

For the canonical Hermes behavior contract — local skill first, Alexandria fallback, Context Vault recall, missing-skill acquisition, and librarian collaboration — see [`docs/project_subject/`](./docs/project_subject/).

The cover art represents the long-term archive direction: skills and prompts are the shelves, Context Vault is the agent memory layer, and MCP is the tool-facing access path.

---

## Current Status

This repository is an active MVP, not a finished product.

Working surfaces include:

- FastAPI backend with archive, category, provider, prompt, skill, MINIO, Context Vault, RAG, and MCP surfaces
- SQLite-backed local development storage with Alembic migrations
- Next.js frontend for dashboard, explore/library, details, settings, providers, imports, Context Vault, capture review, and RAG inspection
- native Typer CLI command tree:
  - `alexandria-hermes`
  - `alex-hermes`
  - `health`, `folders`, `library`, `skills`, `prompts`, `minio`, `context`, `hermes`, `mcp`
- HTTP client paths built on `httpx`
- backend quality gate with `191` passing tests and `pyrefly` clean

Planned/expanding areas:

- richer librarian classification
- deeper prompt and context linting policies
- broader MCP resource/tool coverage
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
ruff format --check: 244 files already formatted
ruff check: All checks passed
pyrefly check: 0 errors
shared guardrails: 25 passed
backend tests: 191 passed
```

Frontend validation:

```bash
cd frontend
npm run security:npm-supply-chain
npm run test:ui-contract
npm run lint
npm run build
```

Latest compose smoke QA covered:

- backend health, archive, usage, provider, Context Vault, RAG status, lint/save/get/chunks/search/access/archive endpoints
- frontend API proxies for Context Vault and RAG
- frontend pages: dashboard, library, settings, agents, contexts, RAG inspector, capture review, context detail
- compose log scan for traceback, unhandled errors, and 500-level failures

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
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
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

`npm run dev` and `npm run start` bind the Next.js server to `127.0.0.1` for
local single-operator safety. Container runs use `npm run dev:container` so the
service binds only inside Docker while Compose still publishes host ports on
`127.0.0.1`.

### Full Stack

```bash
docker compose up --build
```

This starts:

- backend: `http://localhost:8000`
- frontend: `http://localhost:3000`

Compose runs the backend/frontend containers on `0.0.0.0` inside the Docker
network, but host port publishing is restricted to `127.0.0.1` in
`docker-compose.yml`.

During the active npm supply-chain hold, avoid rebuilding the frontend image unless the hold is explicitly lifted, because the frontend Dockerfile runs `npm ci`. If images already exist, use `docker compose up --no-build` for local smoke QA.

---

## CLI

The CLI is a native Typer command tree over the backend HTTP API. It does not bypass backend permissions, validation, duplicate handling, Context Vault rules, or MINIO safety rules.

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
alexandria-hermes context lint ./handoff.md --kind HANDOFF --title "Sprint handoff"
alexandria-hermes context save --content-file ./handoff.md --kind HANDOFF --title "Sprint handoff"
alexandria-hermes context recall "dependency injection" --strategy HYBRID
alexandria-hermes context doctor-rag
alexandria-hermes mcp serve
alexandria-hermes minio scan --limit 24 --json
alexandria-hermes minio import --limit 48
```

Short alias:

```bash
alex-hermes health
```

Hermes integration install/apply flow:

```bash
alexandria-hermes --json hermes onboard \
  --hermes-home ~/.hermes \
  --api-url http://localhost:8000 \
  --install-prompts \
  --install-mcp \
  --dry-run

alexandria-hermes --json hermes onboard \
  --hermes-home ~/.hermes \
  --api-url http://localhost:8000 \
  --install-prompts \
  --install-mcp
```

This installs the Alexandria-Hermes skill/prompt guidance and writes an MCP
config snippet under the Hermes home. For the full install/apply and
no-librarian self-acquisition flow, see
[`install.md`](./install.md).

Configuration:

- default API URL: `http://localhost:8000`
- override with env: `HERMES_API_URL=http://localhost:8000`
- override per command: `--base-url http://localhost:8000`
- use `--json` for agent automation
- without installation, repo-local execution is available via `./bin/alexandria-hermes ...`

---

## Context Vault and RAG

Context Vault stores agent working context as first-class library material.

Supported behaviors:

- lint context Markdown before saving
- redact and score context quality signals
- save handoffs, notes, decisions, compact summaries, and project context
- chunk saved context for retrieval
- recall a Context Pack by query and strategy
- inspect RAG dependency health
- archive entries without hard deletion

Primary surfaces:

- Backend routes under `/library/contexts`
- Frontend pages `/contexts`, `/contexts/{contextId}`, `/capture-review`, `/rag-inspector`
- CLI commands under `alexandria-hermes context ...`
- MCP server via `alexandria-hermes mcp serve`

---

## OpenAI, MINIO, and MCP

### OpenAI

Alexandria-Hermes separates official API usage from ChatGPT/Codex-style OAuth.

Current position:

- supported: `OPENAI` provider with official OpenAI API key
- supported: `OPENAI_CODEX` provider with one-click ChatGPT/Codex OAuth device authorization
- behavior: the settings UI uses server-side Hermes-compatible OAuth defaults, opens the browser authorization page, stores token material only in backend provider secrets, and polls status without putting tokens in browser state
- remaining: using the stored Codex OAuth token for full librarian execution is the next adapter-integration slice; the OAuth lifecycle itself is productized

### MINIO

MINIO is optional. It is intended for teams that already keep skills/prompts as files in object storage.

Recommended model:

- MINIO keeps originals
- Hermes DB stores searchable metadata, classification, folder placement, and object location
- users can scan candidates before importing
- imports should be reviewable and idempotent

### MCP

The MCP server exposes Alexandria-Hermes to MCP-capable agents and tool clients. It should be treated as an agent-facing access path over the same backend contracts, not as a separate business-logic implementation.

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
SERVICE_APP_ENV=local
SERVICE_APP_NAME=alexandria-hermes
SERVICE_OPERATOR_API_KEY=<generate-a-local-operator-key>
```

Codex OAuth follows Hermes Agent's default model: public OpenAI Codex OAuth
metadata is code-owned by the backend, and `.env` is only for local secrets or
explicit operator overrides. Access tokens and refresh tokens are stored only in
backend provider secrets, never in browser state or public config examples.
If an operator must override the Hermes-compatible defaults for a deployment,
set the `SERVICE_CODEX_OAUTH_*` variables locally without committing them.
Sensitive provider/settings routes require `x-operator-api-key`; the
Next.js server proxy forwards it from `ALEXANDRIA_OPERATOR_API_KEY`, and
`docker-compose.yml` maps that value from `SERVICE_OPERATOR_API_KEY`.

---

## Product Philosophy

> Knowledge should not only be stored.  
> It should remain findable, reusable, attributable, and usable by agents at the right moment.

ALEXANDRIA-HERMES aims to become an operational archive where:

- skills are reusable capabilities
- prompts are reusable instruction artifacts
- folders behave like shelves
- context entries preserve what agents learned and decided
- usage history and RAG recall help retrieval
- librarian agents are optional helpers, not hard dependencies
- humans and agents can both participate
