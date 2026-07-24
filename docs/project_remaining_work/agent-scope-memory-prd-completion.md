# Agent Scope Memory PRD Completion

## Scope

This record closes the Alexandria-Hermes Agent Scope Memory PRD implementation
for `SESSION`, `AGENT`, and `PROJECT` Contexts. Platform orchestration, RBAC,
automatic promotion, and other PRD non-goals remain outside this work.

## Task matrix

| Task | Requirement | Status | Evidence |
|---|---|---|---|
| T1 | Scope and identity validation across canonical save/reindex/recall | VERIFIED | Scope validation, round-trip, and strategy consistency tests |
| T2 | Obsidian identity/provenance round trip and SQLite rebuild | VERIFIED | Temporary vault/database reindex evidence |
| T3 | FTS, Vector, and Hybrid scope/lifecycle consistency | VERIFIED | Strategy recall results and lifecycle tests |
| T4 | Content hash, duplicate detection, provenance, and Context Pack | VERIFIED | Repository, Obsidian, retrieval metadata, and pack tests |
| T5 | Archive and explicit bidirectional Supersede capability | VERIFIED | Context API, MCP, canonical lifecycle, idempotency, conflict, and recall tests |
| T6 | P95 performance targets and reproducible acceptance evidence | VERIFIED | Isolated evidence collector under local `docs/jobs/version2_alexandria/evidence` |
| T7 | Full repository quality gate and remote synchronization | PENDING | Updated after final verification and push |

## Explicit Supersede contract

- `POST /memory/contexts/{context_id}/supersede` links two existing
  source-qualified canonical Contexts.
- The replacement receives `supersedes_context_id`; the prior Context receives
  `status: superseded` and `superseded_by_context_id`.
- The replacement forward link is written first so the existing reindex repair
  path can reconcile an interrupted backlink update.
- Exact retries are idempotent and do not increment either version again.
- Missing, self-referential, non-canonical, non-Context, or conflicting
  relations are rejected without rewriting Context bodies.
- The MCP tool `alexandria_supersede_context` exposes the same contract.

## Evidence policy

The repository intentionally ignores `docs/jobs/**` because generated logs and
local execution artifacts are machine-local. The reproducible collector and its
outputs remain in `docs/jobs/version2_alexandria/evidence` locally. This tracked
record stores the durable completion decision; the final verification section
will store the current implementation commit, test run identifier, command
results, and measured P95 values.

## Final verification

Pending the final full quality gate, evidence regeneration, commit, push, and
clean-worktree check.