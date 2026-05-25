# Install Alexandria-Hermes

The frontend runtime has been removed. Install the backend/CLI/MCP service and connect it to Obsidian Markdown.

## Generated vault

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

Open `~/.hermes/alexandria-hermes/data/obsidian-vault` in Obsidian.

## Existing vault named Alexandria

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

Use root `.` when the vault itself is the Alexandria workspace; this avoids `Alexandria/Alexandria` nesting.

## Obsidian side pane

```bash
brew install --cask obsidian
REPO_ROOT="$(git rev-parse --show-toplevel)"
VAULT="$HOME/Desktop/Alexandria"
mkdir -p "$VAULT/.obsidian/plugins"
ln -s "$REPO_ROOT/integrations/obsidian/alexandria-librarian" \
  "$VAULT/.obsidian/plugins/alexandria-librarian"
```

Enable **Alexandria Librarian** in Obsidian Community plugins while the backend is running.

## Docker Compose

```bash
docker compose up --build
```

The backend is available at `http://127.0.0.1:8000`.
