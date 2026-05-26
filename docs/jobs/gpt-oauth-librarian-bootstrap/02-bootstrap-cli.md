---
title: Bootstrap CLI
status: implemented
created: 2026-05-26
updated: 2026-05-26
owner: alexandria-hermes
scope: cli
---

# Bootstrap CLI

## Command

```bash
alexandria-hermes librarian bootstrap-obsidian-oauth \
  --provider-name codex-oauth \
  --model gpt-5.5
```

Optional OAuth start:

```bash
alexandria-hermes librarian bootstrap-obsidian-oauth \
  --provider-name codex-oauth \
  --start-oauth
```

## Behavior

- Creates an `OPENAI_CODEX` + `OAUTH` provider if missing.
- Creates missing default profiles:
  - `research-critic`
  - `obsidian-librarian`
  - `graph-curator`
- Does not attach a preferred provider to new profiles until OAuth execution is
  ready; workflows can still pass `provider_id=codex-oauth` explicitly.
- Redacts OAuth token material from JSON and text output.
