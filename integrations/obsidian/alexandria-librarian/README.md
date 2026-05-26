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
- Keeps a local in-pane conversation history for the current Obsidian session.
- Reads the active Markdown note path and selected text.
- Calls `POST /obsidian/librarian/workflows` by default for LangGraph approval, or `POST /obsidian/librarian/ask` when workflow mode is disabled.
- Renders the Markdown answer, source wikilinks, workflow status badges, and a separate GPT OAuth librarian result panel.
- Shows related notes from `GET /obsidian/notes/by-path/related`.
- Can append the answer to the current note.
- Can add managed Alexandria source wikilinks to the current note.
- Can create context, skill draft, or prompt template notes through `POST /obsidian/notes`.
- Can resume approved LangGraph action cards, including GPT/OAuth librarian delegation, without storing OAuth tokens.

No npm build step is required; `main.js`, `manifest.json`, and `styles.css` are loaded directly by Obsidian.
