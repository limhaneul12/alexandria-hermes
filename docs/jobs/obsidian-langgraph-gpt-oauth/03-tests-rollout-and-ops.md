---
alexandria_type: job_plan
id: job_obsidian_langgraph_gpt_oauth_03_tests_rollout_ops
tags:
  - tests
  - rollout
  - verification
  - ops
status: implemented
created_at: "2026-05-26"
source: codex
---

# Tests, Rollout, and Ops

## Tests

- Workflow pauses and resumes approved writes.
- GPT OAuth delegate service is called when `ask_oauth_librarian` is approved.
- Missing GPT profile degrades to `GUIDANCE_ONLY` instead of failing the workflow.
- LangGraph SQLite checkpoint resumes after service recreation.
- Unknown action and repeated resume are rejected.

## Rollout

1. Run `uv sync` to install `langgraph` and `langgraph-checkpoint-sqlite`.
2. Run migrations as usual; no DB migration is needed for the LangGraph checkpoint file.
3. Ensure `SERVICE_OBSIDIAN_LIBRARIAN_LANGGRAPH_CHECKPOINT_PATH` is writable, or use the default `./data/obsidian_librarian_langgraph.sqlite`.
4. Restart daemon.

## Done criteria

- Backend CI passes.
- Local Obsidian vault smoke starts and resumes a workflow.
- Plugin still installs by copy mode.
- GPT OAuth delegate path is wired through backend provider store, never through plugin secrets.
