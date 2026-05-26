---
alexandria_type: job_plan
id: guide_obsidian_integration_01
tags:
  - alexandria
  - obsidian
  - guidebook
status: active
created_at: "2026-05-25"
source: codex
---

# Obsidian Integration Guide 01 — Vault, SQLite Index, Librarian Chat

Alexandria-Hermes treats Obsidian Markdown as the human-facing durable knowledge store.
SQLite remains a rebuildable cache for search, chunking, and operational state.

```text
Obsidian Markdown = canonical notes
SQLite = search/index/cache
Alexandria-Hermes = backend/CLI/MCP protocol
Librarian = optional Obsidian-aware collaborator
```

## 1. Install and open Obsidian

On macOS, install Obsidian with Homebrew Cask:

```bash
brew install --cask obsidian
```

You can use either:

- the generated Alexandria-Hermes vault at `~/.hermes/alexandria-hermes/data/obsidian-vault`; or
- an existing Obsidian vault such as `~/Desktop/Alexandria`.

The local smoke test used `/Users/imhaneul/Desktop/Alexandria` with Alexandria root `.`.

## 2. Configure Alexandria-Hermes

### Generated vault

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

`--run-migrations` applies Alembic before the first backend/Obsidian call, preventing missing-table errors on `/obsidian/init`.

The generated `.env` includes:

```text
SERVICE_OBSIDIAN_VAULT_PATH=<hermes-home>/alexandria-hermes/data/obsidian-vault
SERVICE_ALEXANDRIA_OBSIDIAN_ROOT=Alexandria
SERVICE_MEMORY_COMPACT_NOTE_DIR=Alexandria/Memory Compacts
```

### Existing `Alexandria` vault

Use this when Obsidian already has a vault at `~/Desktop/Alexandria` and you want the vault itself to be the Alexandria workspace:

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
```

The generated `.env` then includes:

```text
SERVICE_OBSIDIAN_VAULT_PATH=<home>/Desktop/Alexandria
SERVICE_ALEXANDRIA_OBSIDIAN_ROOT=.
SERVICE_MEMORY_COMPACT_NOTE_DIR=Memory Compacts
```

Root `.` prevents a nested `Alexandria/Alexandria` layout.

## 3. Vault layout

Generated-vault mode manages an `Alexandria/` folder inside the vault:

```text
Alexandria/
  START_HERE.md
  Contexts/
  Memory Compacts/
  Skills/
  Prompts/
  Librarian/
    Briefs/
    Chats/
  Jobs/
```

Existing-vault root mode places the same folders directly under the vault root:

```text
START_HERE.md
Contexts/
Memory Compacts/
Skills/
Prompts/
Librarian/
  Briefs/
  Chats/
Jobs/
```

Move files inside Obsidian if needed; Alexandria identifies official notes by frontmatter `id`, not only by path.

## 4. Frontmatter contract

Every Alexandria-managed note starts with YAML frontmatter:

```yaml
---
alexandria_type: context
id: ctx_example
tags:
  - alexandria
status: active
created_at: "2026-05-25T12:00:00Z"
source: mcp
---
```

Supported `alexandria_type` values include `context`, `memory_compact`, `skill`, `prompt`, `librarian_brief`, `librarian_chat`, and `job_plan`.

Notes without this frontmatter can stay in the vault, but reindex skips them as non-Alexandria notes.

## 5. CLI examples

Search notes:

```bash
uv run alexandria-hermes obsidian search "long memory" --type context --tag memory
```

Read by path in generated-vault mode:

```bash
uv run alexandria-hermes obsidian read --path "Alexandria/START_HERE.md"
```

Read by path in existing-vault root mode:

```bash
uv run alexandria-hermes obsidian read --path "START_HERE.md"
```

Save a note from a Markdown body file:

```bash
uv run alexandria-hermes obsidian save "Prompt Draft" \
  --body-file ./prompt.md \
  --type prompt \
  --tag prompt
```

Capture reusable artifacts with migration-safe defaults:

```bash
uv run alexandria-hermes obsidian capture "Browser Verification Skill" \
  --body-file ./skill.md \
  --type skill \
  --project alexandria-hermes \
  --tag browser

uv run alexandria-hermes obsidian capture "Release Review Prompt" \
  --body-file ./prompt.md \
  --type prompt \
  --prompt-kind template
```

`obsidian capture` only accepts `memory_compact`, `skill`, and `prompt`. It
adds artifact tags/frontmatter, writes Markdown as the canonical source, and
updates the SQLite index/cache through the same `/obsidian/notes` path.

Read graph-related notes after reindex:

```bash
uv run alexandria-hermes obsidian related --path "START_HERE.md"
```

Ask the Obsidian-aware librarian:

```bash
uv run alexandria-hermes obsidian ask \
  "이 노트에서 장기기억으로 승격할 내용은?" \
  --active-note-path "Contexts/Today.md" \
  --save-transcript

uv run alexandria-hermes obsidian ask \
  "외부 사서 비평도 같이 받아볼까요?" \
  --delegate \
  --provider-id codex-oauth \
  --profile-id research-critic
```

## 6. MCP tools

Agents can use MCP tools that mirror the CLI:

- `alexandria_reindex_vault`
- `alexandria_search_vault`
- `alexandria_read_note`
- `alexandria_save_note`
- `alexandria_ask_obsidian_librarian`
- `alexandria_get_related_notes`

The intended agent flow is:

```text
search vault → read selected notes → answer/write new Markdown → reindex if needed
```

## 7. Obsidian side pane plugin

A minimal local plugin is available at:

```text
integrations/obsidian/alexandria-librarian/
```

Install it into a vault with the CLI:

```bash
cd backend
uv run alexandria-hermes obsidian install-local \
  --vault-path "$HOME/Desktop/Alexandria" \
  --plugin-install-mode copy
```

Use `copy` for normal installs so plugin settings/data stay in the vault copy instead of the repo. Use `symlink` only when developing the plugin.

Then enable **Alexandria Librarian** from Obsidian Community plugins and run command palette action `Ask Alexandria Librarian`. The pane defaults to **Whole vault** scope: it searches indexed memory, skills, prompts, plans, and context notes, then cites the strongest source notes. Use active-note or selection scope only when the current note should be pinned as extra context. The pane sends the question, project, scope-derived context, note-type filter, source count, and transcript preference to the local backend. It also has a **GPT OAuth connection** card for checking status, starting the device login, opening the verification page, copying the user code, polling after login, and refreshing the backend token.

The side pane now behaves like a small local chat/workflow console:

- session-local conversation history stays inside the pane;
- workflow badges show LangGraph status, delegate status, and transcript saves;
- approval actions render as cards before backend writes or GPT OAuth delegation;
- GPT OAuth librarian output is split into its own panel when the backend appends
  a `## GPT OAuth Librarian` section;
- answer material can be saved as context notes, skill drafts, or prompt
  templates without storing OAuth secrets in the vault.

## 8. Graph relation contract

Alexandria relation frontmatter is rendered into an Obsidian-readable managed wikilink section:

```yaml
source_refs:
  - id: alexandria_start_here
    path: START_HERE.md
    relation: cites
derived_from: []
related: []
supersedes: []
promotes_to: []
```

```md
<!-- ALEXANDRIA-LINKS:START -->
## Alexandria Links

### Sources
- [[START_HERE]] — cites
<!-- ALEXANDRIA-LINKS:END -->
```

SQLite stores this as a rebuildable `obsidian_edges` cache. Related notes are available via CLI, MCP, and HTTP. The Obsidian side pane can show related notes and can write source wikilinks into the active note after user action. LangGraph workflow approval for `add_graph_links` now mutates the active Markdown note server-side, updates the managed Alexandria links section, and reindexes the edge cache before the workflow completes.

## 9. Resumable librarian workflow

The workflow endpoints provide a real LangGraph checkpoint/node runtime:

```text
POST /obsidian/librarian/workflows
GET  /obsidian/librarian/workflows/{thread_id}
POST /obsidian/librarian/workflows/{thread_id}/resume
POST /obsidian/librarian/workflows/{thread_id}/cancel
```

The backend uses `StateGraph` nodes (`collect_context -> plan_actions -> approval_gate -> execute_approved_actions -> finalize`), pauses with `interrupt(...)`, and resumes with `Command(resume={"approved_actions": [...]})`. LangGraph checkpoints persist in `SERVICE_OBSIDIAN_LIBRARIAN_LANGGRAPH_CHECKPOINT_PATH` (default `./data/obsidian_librarian_langgraph.sqlite`), while `obsidian_librarian_workflows` stores API-visible state. Only approved actions are written to Obsidian. Approving `ask_oauth_librarian` calls the backend GPT/OAuth librarian provider/profile through `HermesCollaborationService`; tokens remain in backend provider storage and are never written to the vault or plugin settings. Missing provider/profile settings return `GUIDANCE_ONLY` instead of failing the workflow.

To connect from Obsidian, bootstrap the default provider/profile set once if needed:

```bash
cd backend
uv run alexandria-hermes librarian bootstrap-obsidian-oauth --provider-name codex-oauth
```

Set the plugin **Operator API key** to the local backend `ALEXANDRIA_OPERATOR_API_KEY` first; OAuth lifecycle endpoints are protected. Then use the side-pane **GPT OAuth connection** card: **Start OAuth login** -> finish browser login -> **Poll after login**.

## 10. Librarian chat model

The Obsidian librarian endpoint returns:

- Markdown answer;
- source references with Obsidian wikilinks;
- optional transcript saved under `Librarian/Chats/` or `Alexandria/Librarian/Chats/`, depending on root mode;
- action previews for follow-up note creation;
- delegate status for the optional GPT OAuth librarian lane.

The local answer remains deterministic and source-grounded. Approved GPT/OAuth delegation can now append a `## GPT OAuth Librarian` section when a connected provider/profile returns delegate guidance, without changing the Obsidian note contract.

## 11. Smoke-test evidence

The local `/Users/imhaneul/Desktop/Alexandria` vault was tested with:

```text
SERVICE_OBSIDIAN_VAULT_PATH=/Users/imhaneul/Desktop/Alexandria
SERVICE_ALEXANDRIA_OBSIDIAN_ROOT=.
```

Observed result:

- `START_HERE.md` and `Jobs/Alexandria Obsidian Smoke Test.md` were created.
- Reindex saw 7 Markdown files, indexed 6 Alexandria notes, skipped 1 Obsidian welcome note without Alexandria frontmatter.
- Search found indexed Alexandria notes.
- `obsidian related --path START_HERE.md --limit 5` returned an empty related set, which is valid when no graph edges target or originate from that note yet.
- Delegated librarian ask returned `delegate_status=requested_local_fallback`, `provider_id=codex-oauth`, and `profile_id=research-critic` without saving a transcript.
- LangGraph workflow start/resume smoke moved `waiting_for_approval -> completed`; approving `ask_oauth_librarian` records `GUIDANCE_ONLY` or provider `COMPLETED` depending on configured GPT OAuth provider/profile availability.

## 12. Safety rules

- Do not save raw secrets/API keys/tokens into Obsidian notes.
- Treat Obsidian Markdown as canonical; SQLite can be deleted and rebuilt.
- Resolve conflicts in Obsidian first, then run `alexandria-hermes obsidian reindex`.
- Keep frontend/Next.js removed unless product direction explicitly changes.
