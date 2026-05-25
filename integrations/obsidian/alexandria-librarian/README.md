# Alexandria Librarian Obsidian Plugin

Minimal Obsidian community-plugin bridge for the local Alexandria-Hermes backend.

## Install locally

1. Run the Alexandria-Hermes backend on `http://127.0.0.1:8000`.
2. Copy or symlink this folder into your vault:

   ```bash
   mkdir -p "<vault>/.obsidian/plugins"
   ln -s "$(pwd)/integrations/obsidian/alexandria-librarian" \
     "<vault>/.obsidian/plugins/alexandria-librarian"
   ```

3. In Obsidian, enable community plugins and enable **Alexandria Librarian**.
4. Run command palette action **Ask Alexandria Librarian**.

## What it does

- Opens a right-side `ItemView` chat pane.
- Reads the active Markdown note path and selected text.
- Calls `POST /obsidian/librarian/ask` on the local backend.
- Renders the Markdown answer and source wikilinks.
- Can append the answer to the current note.
- Can create context or skill draft notes through `POST /obsidian/notes`.

No npm build step is required; `main.js`, `manifest.json`, and `styles.css` are loaded directly by Obsidian.
