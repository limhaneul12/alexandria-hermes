---
title: Artifact Round-trip and SQLite Cache Rebuild
id: job_obsidian_canonical_artifacts_02_roundtrip_sqlite_cache
tags:
  - alexandria
  - obsidian
  - sqlite
status: active
source: codex
---

# Artifact Round-trip and SQLite Cache Rebuild

## Rule

The Markdown file is the source of truth. SQLite stores only search/index/cache
rows and operational workflow state.

## Required behavior

1. Capture/save writes a Markdown note with Alexandria frontmatter.
2. Read by note id or path reloads the authoritative Markdown body.
3. Search uses SQLite FTS/chunk rows built from Markdown.
4. Reindexing an empty SQLite cache from the vault restores search/read for
   Memory Compacts, skill drafts, and prompt templates.

## Existing Memory Compact path

Memory Compact lifecycle APIs continue to write Markdown under the configured
`SERVICE_MEMORY_COMPACT_NOTE_DIR`. Those notes are searchable by the Obsidian
index after `/obsidian/index/rebuild` or any search with refresh enabled.

## Migration safety

- `obsidian save` remains a generic managed-note writer.
- `obsidian capture` is restricted to reusable artifact types so old ad hoc
  library imports cannot accidentally create unrelated managed note kinds.
- Secrets are still blocked by the backend note-save redaction guard.
