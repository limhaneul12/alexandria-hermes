# Install

Alexandria-Hermes installs as a backend/CLI/MCP service. The old frontend runtime has been removed.

## Requirements

- Python 3.13 through `uv`
- macOS Homebrew Cask only if you want Codex to install Obsidian locally
- Obsidian for the human-facing Markdown vault

## Backend daemon with generated vault

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

Terminal 2:

```bash
cd backend
uv run alexandria-hermes obsidian init
uv run alexandria-hermes obsidian reindex
```

Open this vault in Obsidian:

```text
~/.hermes/alexandria-hermes/data/obsidian-vault
```

## Backend daemon with an existing Obsidian vault

Use this when you already created `~/Desktop/Alexandria` in Obsidian:

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

`--alexandria-obsidian-root "."` means Alexandria-managed notes live at the vault root, so setup does not create `Alexandria/Alexandria`.

## Install Obsidian and the side-pane plugin

```bash
brew install --cask obsidian
REPO_ROOT="$(git rev-parse --show-toplevel)"
VAULT="$HOME/Desktop/Alexandria"
mkdir -p "$VAULT/.obsidian/plugins"
ln -s "$REPO_ROOT/integrations/obsidian/alexandria-librarian" \
  "$VAULT/.obsidian/plugins/alexandria-librarian"
```

Enable **Alexandria Librarian** in Obsidian Community plugins. Keep the backend running before using the pane.

## Docker Compose

```bash
docker compose up --build
```

The backend is published on `127.0.0.1:8000`.

## Hermes assets

```bash
cd backend
uv run alexandria-hermes hermes onboard
```

Skill/prompt library persistence is no longer SQLite CRUD. Keep reusable assets as Markdown/Obsidian notes until the Obsidian-backed library flow is implemented.
