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
  <a href="https://github.com/limhaneul12/alexandria-hermes/actions/workflows/backend.yml"><img alt="Backend CI" src="https://github.com/limhaneul12/alexandria-hermes/actions/workflows/backend.yml/badge.svg"></a>
  <a href="./LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg"></a>
</p>

# Alexandria-Hermes

Alexandria-Hermes is a FastAPI + MCP backend for agent long-term memory, memory compaction, Obsidian Markdown storage, and librarian collaboration.

The previous Next.js frontend, standalone product CLI, and SQLite-backed skill/prompt/harness CRUD surfaces have been removed. Obsidian Markdown is the human-facing source of truth; SQLite is a rebuildable search/index/cache layer plus operational state.

```text
Obsidian Markdown = canonical notes people can read and edit
SQLite = local index/cache/search and backend operational state
Alexandria-Hermes = FastAPI backend + MCP endpoint
Librarian = optional Obsidian-aware collaborator/chat pane
```

## Current scope

Alexandria-Hermes now focuses on a narrow MCP-first recall surface:

- FastAPI backend on `127.0.0.1:8000`
- Streamable HTTP MCP endpoint at `POST /mcp/`
- MCP tools for Context Vault recall, RAG Context Packs, Memory Compact lookup, librarian collaboration, Obsidian note search/read/save, and skill-acquisition jobs
- SQLite-backed operational storage for provider profiles, OAuth state, librarian jobs, workflow checkpoints, and rebuildable Obsidian/Context search indexes
- Obsidian-backed Markdown notes under `SERVICE_OBSIDIAN_VAULT_PATH`
- Optional local Obsidian plugin at `integrations/obsidian/alexandria-librarian/`

Removed surfaces stay removed by contract tests:

- Next.js/frontend runtime and frontend CI
- standalone product/operator CLI commands
- SQLite library item CRUD, category/folder management, and `app/library` package code
- SQLite-backed skill/prompt/harness CRUD
- MinIO/object-storage archive/import/provider/health surfaces
- public Context Vault lint/manual-save routes

## Quick start

Run the backend with Docker Compose:

```bash
docker compose up --build
```

Or run it locally from `backend/`:

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Required local secret:

```bash
export ALEXANDRIA_OPERATOR_API_KEY="replace-with-at-least-32-characters"
```

Useful Obsidian storage settings:

```bash
export SERVICE_OBSIDIAN_VAULT_PATH="$HOME/Desktop/Alexandria"
export SERVICE_ALEXANDRIA_OBSIDIAN_ROOT="."
export SERVICE_MEMORY_COMPACT_NOTE_DIR="Memory Compacts"
```

Use `SERVICE_ALEXANDRIA_OBSIDIAN_ROOT="."` when the vault itself is the Alexandria workspace. This avoids a nested `Alexandria/Alexandria` layout.

## MCP endpoint

The FastAPI app mounts the MCP server at `/mcp/`. Requests must include the operator API key header:

```text
X-Alexandria-Operator-Key: <ALEXANDRIA_OPERATOR_API_KEY>
```

MCP clients that support Streamable HTTP should connect to:

```text
http://127.0.0.1:8000/mcp/
```

A minimal JSON-RPC initialize smoke request is:

```bash
curl -sS http://127.0.0.1:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Alexandria-Operator-Key: $ALEXANDRIA_OPERATOR_API_KEY" \
  -d '{
    "jsonrpc":"2.0",
    "id":1,
    "method":"initialize",
    "params":{
      "protocolVersion":"2025-06-18",
      "capabilities":{},
      "clientInfo":{"name":"curl-smoke","version":"0.1.0"}
    }
  }'
```

## Obsidian plugin: librarian side pane

The optional local plugin lives at:

```text
integrations/obsidian/alexandria-librarian/
```

Copy or symlink that plugin into the target vault's `.obsidian/plugins/` folder during local plugin development. Then open Obsidian, enable Community plugins, enable **Alexandria Librarian**, and run the command palette action `Ask Alexandria Librarian`.

The pane defaults to **Whole vault** scope so the librarian searches indexed memory, skills, prompts, plans, and context notes before citing source notes. OAuth tokens remain in backend provider storage, not in Obsidian.

## Canonical memory, skills, and prompts

Reusable artifacts live as Obsidian notes, not SQLite library rows. The backend may keep operational job metadata, but the human-editable source of truth is Markdown in the vault.

Memory Compact lifecycle APIs write Markdown under `SERVICE_MEMORY_COMPACT_NOTE_DIR`. Rebuild the Obsidian index with:

```bash
curl -sS -X POST http://127.0.0.1:8000/obsidian/index/rebuild
```

If SQLite is deleted, Markdown can rebuild indexes/caches. Provider profiles, OAuth state, and job/workflow operational state should be backed up separately when needed.

## Graph edges, related notes, and workflows

Reindex rebuilds an `obsidian_edges` cache from relation frontmatter and body wikilinks. Obsidian Markdown remains canonical; deleting SQLite and running reindex rebuilds the cache.

HTTP/MCP additions include related-note retrieval and resumable LangGraph librarian workflows:

```text
GET  /obsidian/notes/by-path/related?path=<path>
GET  /obsidian/notes/{note_id}/related
POST /obsidian/librarian/workflows
GET  /obsidian/librarian/workflows/{thread_id}
POST /obsidian/librarian/workflows/{thread_id}/resume
POST /obsidian/librarian/workflows/{thread_id}/cancel
```

The workflow runtime uses `langgraph` with `StateGraph`, `interrupt(...)`, `Command(resume=...)`, and a SQLite LangGraph checkpoint file. Default checkpoint path: `SERVICE_OBSIDIAN_LIBRARIAN_LANGGRAPH_CHECKPOINT_PATH=./data/obsidian_librarian_langgraph.sqlite`.

## Local development

Backend development uses `uv` and the backend Makefile:

```bash
cd backend
uv sync
uv run ruff check .
uv run pyrefly check
uv run pytest -q
```

The GitHub Actions parity gate is:

```bash
cd backend
make ci
```

Health check:

```bash
curl http://127.0.0.1:8000/health/live
```
