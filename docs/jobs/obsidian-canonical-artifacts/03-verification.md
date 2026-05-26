---
title: Canonical Artifact Verification
id: job_obsidian_canonical_artifacts_03_verification
tags:
  - alexandria
  - obsidian
  - tests
status: active
source: codex
---

# Canonical Artifact Verification

## Regression tests

- CLI `obsidian save` forwards status/source/frontmatter metadata.
- CLI `obsidian capture` creates artifact defaults and rejects non-artifact
  note types.
- Obsidian service round-trips a Memory Compact, skill draft, and prompt
  template after rebuilding an empty SQLite index from the Markdown vault.
- MCP `alexandria_save_note` continues to map to `/obsidian/notes` and now can
  pass optional status/source/frontmatter metadata.

## Rollout checks

Run targeted checks first:

```bash
cd backend
uv run pytest -q tests/cli/test_obsidian_cli.py \
  tests/obsidian/test_obsidian_service.py::test_obsidian_roundtrips_memory_skill_prompt_after_sqlite_rebuild \
  tests/mcp/test_mcp_server.py::test_mcp_obsidian_tools_map_to_vault_endpoints
```

Then run the full backend gate:

```bash
cd backend
make ci
```
