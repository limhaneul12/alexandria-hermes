---
title: Obsidian Canonical Artifacts
id: job_obsidian_canonical_artifacts_00_index
tags:
  - alexandria
  - obsidian
  - canonical-storage
status: active
source: codex
---

# Obsidian Canonical Artifacts

## Objective

Make Obsidian Markdown/frontmatter the canonical surface for the three reusable
Alexandria artifact families the user cares about most:

- Memory Compacts / long-term memory summaries;
- Skill drafts;
- Prompt templates.

SQLite remains a rebuildable search/index/cache. It must be possible to delete
or recreate the SQLite Obsidian index and recover search/read behavior from the
Markdown notes by running reindex.

## Deliverables

| File | Purpose |
| --- | --- |
| [01-capture-command.md](01-capture-command.md) | CLI/MCP capture/save contract for canonical artifacts |
| [02-roundtrip-sqlite-cache.md](02-roundtrip-sqlite-cache.md) | Round-trip and rebuild expectations |
| [03-verification.md](03-verification.md) | Tests, docs, and rollout checks |

## Non-goals

- Restore SQLite-primary skill/prompt CRUD.
- Store OAuth tokens, provider secrets, or raw credentials in Obsidian notes.
- Reintroduce the removed frontend.
