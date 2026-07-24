# Agent Scope Memory Acceptance Evidence

- Test Run ID: `agent-scope-memory-20260724-ca32547`
- Implementation Git Commit SHA: `ca32547`
- Verification date: `2026-07-24` (Asia/Seoul)
- Isolation: temporary Obsidian Vault and temporary SQLite database
- Workspace boundary: explicit `workspace_id=default`

## Included evidence

- `collect_evidence.py`: reproducible isolated evidence collector.
- `generated-agent-context.md`: Markdown emitted by the canonical writer.
- `reindex-result.json`: deleted SQLite index followed by full Markdown reindex.
- `recall-results.json`: FTS, Vector, and Hybrid scope-boundary results.
- `performance.json`: isolated P95 measurements and PRD targets.
- `test-run.log`: exact final repository quality-gate output.

## Verified results

- Four Context notes were saved and all four reindexed with zero errors.
- Scope, project, workspace, Agent, Session, lifecycle, version, content hash,
  and provenance identifiers survived the round trip.
- FTS, Vector, and Hybrid each returned only `ctx_agent_a` and
  `ctx_project_shared` for Agent A plus Project recall.
- P95: FTS `9.663ms` <= `500ms`; Hybrid `14.456ms` <= `2000ms`; Context
  save `21.047ms` <= `1000ms`.
- Official gate: dependency audit succeeded, Ruff passed, Pyrefly reported
  zero errors, and Pytest completed with `535 passed`.

## Reproduce

From `backend/`, run:

```bash
PYTHONPATH=. \
EVIDENCE_DIR=../docs/project_remaining_work/agent-scope-memory-evidence \
TEST_RUN_ID=<run-id> \
GIT_COMMIT_SHA=$(git rev-parse HEAD) \
uv run python ../docs/project_remaining_work/agent-scope-memory-evidence/collect_evidence.py
```
