# Alexandria Librarian Obsidian Plugin

Minimal Obsidian community-plugin bridge for the local Alexandria-Hermes backend.

## Install locally

1. Run the Alexandria-Hermes backend on `http://127.0.0.1:8000`.
2. Install this folder into your vault with the CLI:

   ```bash
   cd backend
   uv run alexandria-hermes obsidian install-local \
     --vault-path "<vault>" \
     --plugin-install-mode copy
   ```

   Copy mode avoids repo-local `data.json` writes. Use `symlink` only while developing this plugin.

3. In Obsidian, enable community plugins and enable **Alexandria Librarian**.
4. Run command palette action **Ask Alexandria Librarian**.

## What it does

- Opens a right-side `ItemView` chat pane.
- Reads the active Markdown note path and selected text.
- Calls `POST /obsidian/librarian/ask` on the local backend.
- Renders the Markdown answer and source wikilinks.
- Shows related notes from `GET /obsidian/notes/by-path/related`.
- Can append the answer to the current note.
- Can add managed Alexandria source wikilinks to the current note.
- Can create context or skill draft notes through `POST /obsidian/notes`.
- Can send provider/profile ids plus an explicit delegate flag without storing OAuth tokens.

No npm build step is required; `main.js`, `manifest.json`, and `styles.css` are loaded directly by Obsidian.
