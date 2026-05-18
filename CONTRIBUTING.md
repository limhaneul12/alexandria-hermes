# Contributing to Alexandria-Hermes

Thanks for helping improve Alexandria-Hermes.

This project is a local-first agent library and recall layer for reusable skills, prompts, contexts, memory compacts, and optional librarian curation.

## Before you start

Read:

- `README.md`
- `install.md`
- `SECURITY.md`
- `backend/AGENTS.md` before backend changes
- `docs/usage_guidebook/README.md` before docs changes

## Development setup

Backend:

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm run security:npm-supply-chain
npm run dev
```

The npm supply-chain hold is active. Do not run `npm install`, `npm uninstall`, `npm ci`, or `npx` unless maintainers explicitly lift the hold for that task.

## Quality gates

Backend:

```bash
cd backend
make ci
```

Frontend:

```bash
cd frontend
npm run security:npm-supply-chain
npm run lint
npm run test:ui-contract
npm run test:librarian-chat
npm run test:library-ui-navigation
npm run test:content-viewer
npm run test:library-category-filter
npm run test:ask-librarian-widget
npm run test:agent-route-payload
npm run build
```

If `next build` fails with a generated `.next` scandir/cache error, remove generated artifacts and retry:

```bash
rm -rf frontend/.next
```

## Backend rules

Backend changes must follow `backend/AGENTS.md` and its rule documents.

Highlights:

- external I/O DTOs use Pydantic v2 schemas
- internal object DTOs use dataclasses where appropriate
- dictionary payload contracts use TypedDict
- route/service/repository boundaries should stay concept-owned
- additive migrations only for persisted schema changes
- no ad hoc direct environment reads inside service/domain/router/provider code

## Docs rules

Docs should be task-oriented:

```text
When to use
→ prerequisites
→ commands/API/MCP example
→ expected output
→ common failures
```

Never include real secrets. Use `<operator-key>` or `[REDACTED]`.

## Pull request checklist

- [ ] Scope is narrow and described clearly.
- [ ] Security implications are considered.
- [ ] Docs are updated for user-facing behavior.
- [ ] Backend quality gates pass if backend changed.
- [ ] Frontend quality gates pass if frontend changed.
- [ ] No generated runtime DB/model/cache files are committed.
- [ ] No raw secrets appear in code, docs, tests, logs, or screenshots.

## License note

Alexandria-Hermes is distributed under the MIT License. See [`LICENSE`](./LICENSE).
