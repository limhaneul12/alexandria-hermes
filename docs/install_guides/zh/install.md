# Alexandria-Hermes install

The frontend runtime has been removed. Install the backend/CLI/MCP service and connect it to an Obsidian Markdown vault.

## Generated vault

```bash
cd backend
uv sync
uv run alexandria-hermes setup --mode backend-daemon --apply --write-guidebook
uv run alexandria-hermes serve \
  --env-file "$HOME/.hermes/alexandria-hermes/.env" \
  --host 127.0.0.1 \
  --port 8000
```

In another terminal after the backend starts:

```bash
cd backend
uv run alexandria-hermes obsidian init
uv run alexandria-hermes obsidian reindex
```

Open `~/.hermes/alexandria-hermes/data/obsidian-vault` in Obsidian.

## Existing `Alexandria` vault

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

Root `.` means the vault itself is the Alexandria workspace and prevents an `Alexandria/Alexandria` nested layout.

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
