# Alexandria-Hermes

Alexandria-Hermes is a backend/CLI/MCP service for agent long-term memory, memory compaction, Obsidian Markdown storage, and librarian collaboration.

The previous Next.js frontend and SQLite-backed skill/prompt/harness CRUD surfaces have been removed. Obsidian Markdown is the human-facing source of truth; SQLite is a rebuildable search/index/cache layer plus operational state.

```text
Obsidian Markdown = canonical notes people can read and edit
SQLite = local index/cache/search and backend operational state
Alexandria-Hermes = FastAPI + CLI + MCP protocol
Librarian = optional Obsidian-aware collaborator/chat pane
```

## What remains

- FastAPI backend on `127.0.0.1:8000`
- CLI entrypoint: `alexandria-hermes`
- MCP tools for Context Vault, Memory Compact, librarian collaboration, and skill-acquisition jobs
- SQLite-backed operational storage for provider/librarian jobs and Context RAG indexes
- Obsidian-backed Markdown notes under `SERVICE_OBSIDIAN_VAULT_PATH`
- Optional local Obsidian plugin at `integrations/obsidian/alexandria-librarian/`

## Quick start: generated Obsidian vault

Terminal 1:

```bash
cd backend
uv sync
uv run alexandria-hermes setup --mode backend-daemon --apply --write-guidebook --run-migrations
uv run alexandria-hermes serve \
  --env-file "$HOME/.hermes/alexandria-hermes/.env" \
  --host 127.0.0.1 \
  --port 8000
```

Terminal 2, after the backend is running:

```bash
cd backend
uv run alexandria-hermes obsidian init
uv run alexandria-hermes obsidian reindex
```

Open the generated vault path in Obsidian:

```text
~/.hermes/alexandria-hermes/data/obsidian-vault
```

## Quick start: existing vault named `Alexandria`

If you already created an Obsidian vault such as `~/Desktop/Alexandria`, point setup at that vault and manage the vault root directly:

```bash
cd backend
uv sync
uv run alexandria-hermes setup \
  --mode backend-daemon \
  --apply \
  --write-guidebook \
  --run-migrations \
  --obsidian-vault-path "$HOME/Desktop/Alexandria" \
  --alexandria-obsidian-root "."
uv run alexandria-hermes serve \
  --env-file "$HOME/.hermes/alexandria-hermes/.env" \
  --host 127.0.0.1 \
  --port 8000
```

Use `--alexandria-obsidian-root "."` when the vault itself is the Alexandria workspace. This avoids a nested `Alexandria/Alexandria` layout.

Smoke-tested local vault: `/Users/imhaneul/Desktop/Alexandria` with root `.`. Reindex saw 7 Markdown files, indexed 6 Alexandria notes, skipped the default welcome note without Alexandria frontmatter, verified plugin copy install, and confirmed delegated librarian ask falls back transparently to the local librarian when no OAuth provider runner is attached.

## Obsidian plugin: librarian side pane

Install the local plugin into the target vault:

```bash
cd backend
uv run alexandria-hermes obsidian install-local \
  --vault-path "$HOME/Desktop/Alexandria" \
  --plugin-install-mode copy
```

`copy` is the default and avoids Obsidian writing plugin `data.json` into the repo. Use `--plugin-install-mode symlink` only for plugin development.

Then open Obsidian, enable Community plugins, enable **Alexandria Librarian**, and run the command palette action `Ask Alexandria Librarian`. The pane sends the active note path, selected text, question, project, transcript preference, optional provider/profile ids, and explicit OAuth-delegate flag to the local backend.

## Graph edges, related notes, and workflows

Reindex now rebuilds an `obsidian_edges` cache from relation frontmatter and body wikilinks. Obsidian Markdown remains canonical; deleting SQLite and running reindex rebuilds the cache.

```bash
uv run alexandria-hermes obsidian related --path "START_HERE.md"
uv run alexandria-hermes obsidian ask "정리해줘" --delegate --provider-id codex-oauth --profile-id research-critic
```

HTTP/MCP additions include related-note retrieval and resumable LangGraph librarian workflows:

```text
GET  /obsidian/notes/by-path/related?path=<path>
GET  /obsidian/notes/{note_id}/related
POST /obsidian/librarian/workflows
GET  /obsidian/librarian/workflows/{thread_id}
POST /obsidian/librarian/workflows/{thread_id}/resume
```

The workflow runtime now uses the real `langgraph` package with `StateGraph`, `interrupt(...)`, `Command(resume=...)`, and a SQLite LangGraph checkpoint file. Default checkpoint path: `SERVICE_OBSIDIAN_LIBRARIAN_LANGGRAPH_CHECKPOINT_PATH=./data/obsidian_librarian_langgraph.sqlite`. Approving `ask_oauth_librarian` routes to the backend GPT/OAuth librarian provider/profile when connected; missing providers/profiles degrade to guidance-only without writing OAuth secrets into Obsidian.

## Local development

```bash
cd backend
uv sync
uv run ruff check .
uv run pyrefly check
uv run pytest -q
```

Run the backend with Docker Compose:

```bash
docker compose up --build
```

Health check:

```bash
curl http://127.0.0.1:8000/health/live
```

## Direction

Use Obsidian/Markdown as the human-facing library surface. Alexandria-Hermes should provide the agent-facing protocol: recall durable memory, prepare compacts as Obsidian notes, ask or route librarian work, and preserve skill-acquisition job results without reintroducing a web UI.
