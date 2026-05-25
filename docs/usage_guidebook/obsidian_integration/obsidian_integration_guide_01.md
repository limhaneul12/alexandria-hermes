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
uv run alexandria-hermes setup --mode backend-daemon --apply --write-guidebook
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

Ask the Obsidian-aware librarian:

```bash
uv run alexandria-hermes obsidian ask \
  "이 노트에서 장기기억으로 승격할 내용은?" \
  --active-note-path "Contexts/Today.md" \
  --save-transcript
```

## 6. MCP tools

Agents can use MCP tools that mirror the CLI:

- `alexandria_reindex_vault`
- `alexandria_search_vault`
- `alexandria_read_note`
- `alexandria_save_note`
- `alexandria_ask_obsidian_librarian`

The intended agent flow is:

```text
search vault → read selected notes → answer/write new Markdown → reindex if needed
```

## 7. Obsidian side pane plugin

A minimal local plugin is available at:

```text
integrations/obsidian/alexandria-librarian/
```

Install it into a vault by copying or symlinking the folder:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
VAULT="$HOME/Desktop/Alexandria"
mkdir -p "$VAULT/.obsidian/plugins"
ln -s "$REPO_ROOT/integrations/obsidian/alexandria-librarian" \
  "$VAULT/.obsidian/plugins/alexandria-librarian"
```

Then enable **Alexandria Librarian** from Obsidian Community plugins and run command palette action `Ask Alexandria Librarian`. The pane sends the active note path, selected text, question, project, and transcript preference to the local backend.

## 8. Librarian chat model

The Obsidian librarian endpoint returns:

- Markdown answer;
- source references with Obsidian wikilinks;
- optional transcript saved under `Librarian/Chats/` or `Alexandria/Librarian/Chats/`, depending on root mode;
- action previews for follow-up note creation.

The current backend implementation is deterministic and source-grounded. It can later delegate to an external librarian provider without changing the Obsidian note contract.

## 9. Smoke-test evidence

The local `/Users/imhaneul/Desktop/Alexandria` vault was tested with:

```text
SERVICE_OBSIDIAN_VAULT_PATH=/Users/imhaneul/Desktop/Alexandria
SERVICE_ALEXANDRIA_OBSIDIAN_ROOT=.
```

Observed result:

- `START_HERE.md` and `Jobs/Alexandria Obsidian Smoke Test.md` were created.
- Reindex saw 5 Markdown files, indexed 4 Alexandria notes, skipped 1 Obsidian welcome note without Alexandria frontmatter.
- Search found the smoke note.
- Librarian ask returned 2 source references and saved a transcript under `Librarian/Chats/`.

## 10. Safety rules

- Do not save raw secrets/API keys/tokens into Obsidian notes.
- Treat Obsidian Markdown as canonical; SQLite can be deleted and rebuilt.
- Resolve conflicts in Obsidian first, then run `alexandria-hermes obsidian reindex`.
- Keep frontend/Next.js removed unless product direction explicitly changes.
