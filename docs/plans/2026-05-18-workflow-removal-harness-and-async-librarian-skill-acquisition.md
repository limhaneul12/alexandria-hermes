# WORKFLOW Removal, Harness Design, and Async Librarian Skill Acquisition Plan

## Status

- **WORKFLOW removal:** implemented in the current working tree.
- **Harness:** not implemented yet; keep as a separate design/implementation slice.
- **Async librarian skill acquisition:** not implemented yet; keep as a separate durable-job slice.

## Product Decisions

1. `WORKFLOW` is not an active product surface and should be removed.
2. `WORKFLOW` should **not** be renamed into `HARNESS` as-is.
3. `HARNESS` should mean agent-owned execution memory: what task ran, how it ran, which commands/tests/evidence were used, what failed, what changed, and how to reuse that procedure later.
4. Missing-skill acquisition must become asynchronous: Hermes can keep working while a librarian generates/acquires a skill, then resume later from durable handles.

## WORKFLOW Removal Scope

Implemented removal targets:

- Removed `/library/workflows` FastAPI router wiring.
- Removed workflow application service and workflow-specific schemas/enums.
- Removed `ItemType.WORKFLOW` from the active library item enum.
- Removed `/retrieval/search/library/workflows` legacy search endpoint.
- Removed workflow-specific DI provider wiring.
- Updated archive import heuristic so workflow/checklist/runbook text no longer creates `WORKFLOW` items.
- Updated librarian lightweight classifier so it no longer emits `WORKFLOW`.
- Updated frontend library item type contract so backend-visible item types no longer include `WORKFLOW`.
- Added a forward migration that deletes legacy `WORKFLOW` rows/usage and removes `WORKFLOW` from the active `library_items.item_type` CHECK constraint.
- Removed workflow i18n labels.
- Added pruning contract tests proving the route and item type stay removed.

Primary files changed:

```text
backend/app/library/interface/routers/workflow_router.py                      deleted
backend/app/library/application/workflow_service.py                           deleted
backend/app/library/interface/schemas/workflow/workflow_schema.py             deleted
backend/app/library/domain/event_enum/workflow_enums.py                       deleted
backend/app/library/domain/event_enum/item_enums.py                           updated
backend/app/library/containers.py                                             updated
backend/app/main.py                                                           updated
backend/app/retrieval/interface/routers/search_router.py                      updated
backend/app/archive/application/minio/use_cases/import_archive_items.py        updated
backend/app/librarian/application/librarian_ops_service.py                    updated
backend/migrations/versions/202605181430_remove_workflow_library_item_type.py     added
backend/tests/platform/test_alembic_migrations.py                              updated
backend/tests/library/interface/test_workflow_pruning_contract.py             added
frontend/src/types/library.ts                                                 updated
frontend/src/lib/i18n.ts                                                      updated
```

## Verification Already Run

Backend:

```bash
cd backend
UV_PROJECT_ENVIRONMENT=/tmp/alexandria-hermes-backend-uv-env uv run pytest -q \
  tests/library/interface/test_workflow_pruning_contract.py \
  tests/library/interface/test_item_family_router.py \
  tests/library/interface/test_backend_routers.py \
  tests/archive/application/test_minio_archive_import.py

UV_PROJECT_ENVIRONMENT=/tmp/alexandria-hermes-backend-uv-env make ci
```

Observed result:

```text
focused: 13 passed
make ci: ruff format/check passed, pyrefly 0 errors, guardrails 33 passed, pytest 329 passed
```

Frontend:

```bash
cd frontend
npm run test:library-ui-navigation
npm run test:ui-contract
npm run lint
npm run build
```

Observed result:

```text
library UI navigation contract ok
product UI contract ok
ESLint: No issues found
Next build compiled successfully and generated 31 static pages
```

Note: frontend `.next` had local duplicate-copy artifacts such as `.next/server 2`; deleting `.next` fixed the build cache issue.

## Remaining Harness Design Slice

`HARNESS` should be designed independently from the removed `WORKFLOW` CRUD surface.

Candidate domain:

```text
HarnessRecord
- id
- title
- goal
- project
- trigger/query
- procedure steps
- commands run
- files touched
- tests/verification evidence
- failures and fixes
- related context ids
- related skill ids
- created_by_agent
- created_at / updated_at
```

Rules:

- Agent-generated only.
- No human manual create/review workflow.
- Human can search, view, archive/delete, maybe lightly edit metadata later.
- Recall should help future similar tasks choose a proven procedure.

## Remaining Async Librarian Skill Acquisition Slice

Target flow:

```text
Hermes local skill miss
→ Alexandria skill/library search miss
→ librarian route/search miss
→ librarian suggests acquisition/generation
→ durable async job created
→ Hermes keeps working
→ librarian returns structured skill artifact
→ skill is persisted through agent write path
→ related context/memory is captured
→ Hermes receives resume packet with skill_id/context_id/job_id
```

Missing capabilities to implement:

- Durable job model/table.
- Job status endpoint and MCP polling tool.
- Background librarian execution.
- Structured skill artifact schema.
- Automatic skill persistence via agent write path.
- Context Vault capture for why/how the skill was acquired.
- Resume packet for Hermes.

## Safety Notes

- Do not remove MCP agent write paths.
- Keep `/library/skills/submit-by-agent` and skill-acquisition tools.
- Deleting `WORKFLOW` is separate from deleting or weakening agent memory/skill capture.
