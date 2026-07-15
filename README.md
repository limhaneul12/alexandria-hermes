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
- Minimal package CLI for launching MCP and checking librarian readiness
- MCP tools for Context Vault recall, RAG Context Packs, Memory Compact lookup, librarian collaboration, Obsidian note search/read/save, and skill-acquisition jobs
- SQLite-backed operational storage for provider profiles, OAuth state, librarian jobs, workflow checkpoints, and rebuildable Obsidian/Context search indexes
- Obsidian-backed Markdown notes under `SERVICE_OBSIDIAN_VAULT_PATH`
- Optional local Obsidian plugin at `integrations/obsidian/alexandria-librarian/`

Removed legacy surfaces stay removed by contract tests:

- Next.js/frontend runtime and frontend CI
- standalone product/operator CRUD CLI commands
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

After the backend is running, verify the second-brain/librarian bridge with the
package CLI, not Makefile operational wrappers. Install/sync once, then use
`--no-sync` for parseable JSON stdout:

```bash
cd backend
make install-local
uv run --no-sync --no-editable alexandria-hermes librarian check \
  --project alexandria-hermes \
  --refresh-compact \
  --summary
```

The command returns parseable JSON and repairs only stale or missing CURRENT
Memory Compacts. A healthy local bridge returns `ok: true`, empty `warnings`,
healthy RAG fields, `review_queue_total: 0`, and a current compact id/age.
When attention is needed, the summary includes `next_actions_count`,
`next_action`, `next_action_tool`, `review_auto_move_candidates`, and
`review_manual_required` so an agent can choose the next safe librarian
operation without reading a long diagnostic body.

## MCP endpoint

The FastAPI app mounts the MCP server at `/mcp/`. Requests must include the operator API key header:

```text
X-Alexandria-Operator-Key: <ALEXANDRIA_OPERATOR_API_KEY>
```

MCP clients that support Streamable HTTP should connect to:

```text
http://127.0.0.1:8000/mcp/
```

After changing or reinstalling the backend, an MCP `tools/list` smoke check should
include the librarian readiness and curation tools:

```bash
cd backend
uv run --no-sync --no-editable alexandria-hermes mcp smoke-tools
```

```text
alexandria_librarian_readiness
alexandria_librarian_refresh_current_compact
alexandria_librarian_review_queue
alexandria_librarian_review_move_plan
alexandria_librarian_review_apply_moves
```

To check both MCP tool exposure and librarian readiness in one script-friendly
JSON result, run:

```bash
cd backend
uv run --no-sync --no-editable alexandria-hermes librarian check \
  --project alexandria-hermes
```

For a status-only JSON result, including MCP endpoint/tool count, tool exposure,
required MCP librarian tool names, RAG health, review queue total,
automatic/manual curation counts, the current compact id/age, and the first
recommended librarian action, add `--summary`:

```bash
cd backend
uv run --no-sync --no-editable alexandria-hermes librarian check \
  --project alexandria-hermes \
  --summary
```

For startup automation that also repairs only stale or missing CURRENT compacts,
add `--refresh-compact`:

```bash
cd backend
uv run --no-sync --no-editable alexandria-hermes librarian check \
  --project alexandria-hermes \
  --refresh-compact \
  --summary
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

## Librarian readiness CLI

The package CLI is a Typer command package under `backend/app/cli/`. It includes
only operational commands that support the MCP-first librarian workflow; it does
not restore the removed product CRUD CLI.

Run a one-shot readiness check against the local backend:

```bash
cd backend
uv run --no-sync --no-editable alexandria-hermes librarian readiness \
  --project alexandria-hermes
```

The response combines RAG health, CURRENT Memory Compact freshness, and the
librarian review queue. A healthy second-brain bridge should return
`"status": "ready"`, an empty `warnings` list, and an empty `next_actions`
list. If attention is needed, `next_actions` gives deterministic priorities for
repairing retrieval, refreshing the CURRENT compact, planning safe vault moves
for automatic candidates, or inspecting notes that still require human/librarian
judgment. The embedded `review_queue` also separates automatic move candidates
from manual-review notes before applying changes.

Inspect the curation queue directly without changing the vault:

```bash
cd backend
uv run --no-sync --no-editable alexandria-hermes librarian review-queue \
  --project alexandria-hermes \
  --summary
```

Build the non-mutating safe move plan for automatic candidates:

```bash
cd backend
uv run --no-sync --no-editable alexandria-hermes librarian review-move-plan \
  --project alexandria-hermes
```

After inspecting the plan, apply the safe moves explicitly and write an
operation report. Direct CLI use must include `--confirm-apply` when the plan has
move candidates. The MCP apply tool follows the same default: it returns
`confirmation_required` unless `confirm_apply` is true for a non-empty plan.

```bash
cd backend
uv run --no-sync --no-editable alexandria-hermes librarian review-apply-moves \
  --project alexandria-hermes \
  --confirm-apply
```

Review commands accept `--project`, `--limit`, and optional `--scope-path`; the
apply command also accepts optional `--report-path` and `--verification-query`.

Use preflight in scripts or agent startup checks. It prints the same JSON-shaped
readiness evidence, returns exit code `0` when ready, and returns exit code `2`
when the librarian still needs attention:

```bash
cd backend
uv run --no-sync --no-editable alexandria-hermes librarian preflight \
  --project alexandria-hermes
```

Plan a CURRENT Memory Compact refresh without mutating the vault:

```bash
cd backend
uv run --no-sync --no-editable alexandria-hermes librarian refresh-current-compact \
  --project alexandria-hermes
```

Apply the refresh only when the plan says `refresh_required: true`, or when an
operator intentionally passes `--force`:

```bash
cd backend
uv run --no-sync --no-editable alexandria-hermes librarian refresh-current-compact \
  --project alexandria-hermes \
  --apply
```

For a startup check that may repair only stale or missing CURRENT compacts, use:

```bash
cd backend
uv run --no-sync --no-editable alexandria-hermes librarian preflight \
  --project alexandria-hermes \
  --refresh-compact
```

This passes `--refresh-compact`, but it remains a no-op when the CURRENT compact
is already fresh (`refresh_required: false`, `created: null`). It only creates a
new CURRENT compact when readiness reports a missing, stale, or timestamp-less
compact. Use `--max-compact-age-days 14` to tighten freshness during a check.

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

`make ci` also runs a no-editable package CLI smoke check for both
`alexandria-hermes` and `alex-hermes`.

Health check:

```bash
curl http://127.0.0.1:8000/health/live
```
