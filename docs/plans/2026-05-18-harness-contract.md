# Agent-Owned HARNESS Contract

`HARNESS` is execution memory for future agents. It is **not** the removed
`WORKFLOW` CMS surface under a new name.

## Ownership

- Owner: Context Vault / memory bounded context.
- Writer: agent or MCP tool after real work has happened.
- Reader: recall/RAG paths that help future agents reuse an observed procedure.
- Non-owner: frontend manual CRUD and `/library/*` item authoring.

## Required semantics

A harness records:

- task goal
- project/repo scope
- environment
- trigger context
- ordered execution trace
- commands and tests run
- failures and fixes
- resulting artifact handles
- reusable procedure
- recall keywords
- safety and side-effect notes
- restore prompt for future agents

## Backend contract

Harnesses are stored as `ContextKind.HARNESS` Context Vault entries through:

```text
POST /memory/contexts/harnesses/capture
```

They are searchable through the existing Context Vault retrieval endpoint with
`kind=HARNESS`. There is intentionally no `/library/harnesses` route and no
manual frontend create/edit surface.

## MCP contract

Hermes uses `alexandria_capture_harness` to persist a sanitized execution trace
after completing useful work. The tool writes through the backend HTTP API; it
does not access the database directly.
