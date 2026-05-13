# Repository Guidelines

## Project Structure & Module Organization
This repo is a two-service starter:
- `backend/` Python FastAPI service
  - `backend/app/` application code (entrypoint: `backend/app/main.py`)
  - `backend/app/platform/` platform logic (routing, middleware, lifecycle, config, logging)
  - `backend/app/shared/` reusable helpers and guardrails
  - `backend/tests/` backend tests (`test_*.py`)
- `frontend/` Next.js app (`frontend/src/`)
- `docker-compose.yml` for local orchestration
- `README.md` for high-level startup notes

## Build, Test, and Development Commands
### Backend (Python)
```bash
cd backend
uv sync
uv run ruff check .        # lint
uv run ruff format .       # format
uv run pyrefly check       # type/safety check
uv run pytest -q          # run backend tests
```
### Frontend (TypeScript)
```bash
cd frontend
# SECURITY HOLD: do not run npm install, npm uninstall, npx, or other package-manager install/remove commands unless the npm supply-chain incident hold is explicitly lifted.
npm run security:npm-supply-chain  # offline lockfile/payload guard
npm run dev      # start Next.js dev server on :3000
npm run build    # production build
npm run lint     # eslint
```
### Full stack
```bash
docker compose up --build
```
Starts both backend (`:8000`) and frontend (`:3000`).

## Coding Style & Naming Conventions
- Python: target `3.13` (`pyproject.toml`) with `ruff` formatting rules.
  - 88-char line length, 4-space indentation, double quotes.
  - Prefer explicit module paths (`app.platform...`), Pydantic models, and typed public functions.
  - Docstrings should use `Args:` / `Return:` sections.
- TypeScript/React: follow existing Next.js defaults (`eslint`, TypeScript strictness via `tsconfig`).
- Naming:
  - Python: `snake_case` for functions/variables, `PascalCase` for classes.
  - Paths/files should reflect domain (`platform`, `shared`, `schemas`, `util`, `middleware`).

## Testing Guidelines
- Backend test framework: `pytest`.
- Tests are discovered under `backend/tests/` and named `test_*.py`.
- Run `uv run pytest -q` before review.
- Keep tests fast and deterministic; avoid external service dependencies in default suite.

## Commit & Pull Request Guidelines
- `git log` currently has only an initial commit; use a consistent convention such as:
  - `feat: add ...`, `fix: ...`, `refactor: ...`, `chore: ...`
- PRs should include:
  - concise summary + impacted areas
  - validation run command outputs
  - risk/rollback notes when touching lifecycle, config, or logging behavior

## Security & Configuration Tips
- NPM supply-chain incident hold: until explicitly lifted, do not run `npm install`, `npm uninstall`, `npx`, or package-manager install/remove commands. Prefer offline lockfile/payload checks such as `npm run security:npm-supply-chain`, and rotate credentials if a compromised package was installed.
- Runtime config is environment-based (`.env`, `SERVICE_` prefix for app config, `STREAM_` for stream config).
- Avoid committing secrets; keep local credentials in local env files only.
- For local health checks, keep backend exposed only as needed and verify startup endpoints via:
  - `http://localhost:8000/health/live`


# Testing Rules

Rules for any agent (Claude Code, Codex, Cursor) writing or modifying tests in this repo.
Drop this file at the project root. Agents read it automatically.

## Core Philosophy

1. Test behavior, not implementation. Pure refactors must not break tests.
2. Mock only at the system boundary. Everything inside is real.
3. Prefer Classist (Chicago) TDD. Mockist (London) rots fast in AI-driven codebases.
4. Fewer meaningful tests beat many leaky ones.

## Mocking Rules

**Mock these** — and only these:
- Database / ORM
- Third-party HTTP APIs
- Filesystem, clock, randomness, network
- Anything crossing a process boundary

**Never mock these:**
- Value objects, DTOs, entities you own
- Pure functions and utilities
- Internal collaborators (services/modules in the same codebase)
- The unit under test (if tempted, your unit boundary is wrong)

Prefer an HTTP-level fake (e.g. `wiremock`, `msw`, `nock`) over a trait/interface mock.
Prefer a real temp filesystem (`tempfile`, `tmp.dirSync()`) over a mocked `fs`.

## Assertion Rules

- Assert on **return values** and **observable state**.
- Do not make `toHaveBeenCalledWith(...)` / `verify(...)` / `expect(spy).toBe(...)` the primary verification.
- Compare whole objects over field-by-field assertions (`expect(result).toEqual(expected)`).
- Never snapshot non-deterministic output (LLM text, timestamps, ordering-free sets).

## Naming Rules

Test names state observable behavior. Never method names or internal calls.

```
// Bad — implementation-flavored
test_findUnique_called_once()
test_calls_upsert_then_emits_event()
should_work()

// Good — behavior
returns_cached_result_when_fetched_within_ttl()
rejects_login_when_password_is_expired()
charges_full_price_for_non_vip_users()
```

Template: `<subject>_<expected_behavior>_when_<condition>`

## Structure Rules

| Layer | Purpose | Budget |
|---|---|---|
| Unit | Pure logic, entities, utils | Many, in-memory, milliseconds |
| Integration | Module + real DB/queue | Moderate, per critical module |
| E2E | Critical user journeys | Few, one per journey |
| Regression | One per past incident | As bugs happen |

- One E2E per critical journey. A handful of integration tests per domain.
- Unit tests only where logic is non-trivial. No unit tests for getters, DI wiring, or framework glue.
- Colocate unit specs next to source. Keep integration/E2E in a separate tree.
- Gate expensive live tests behind an env flag (`LIVE_TEST=true`, `RUN_EXPENSIVE=1`).

## Domain Entity Rules

Extract a domain entity when **any** of these are true:
- Business logic is scattered across 2+ services on the same data.
- A service does arithmetic or state transitions on a plain DB row.
- You need to spin up a DB to test logic that is secretly pure.

```
# Before — logic in the service, tied to ORM
user.hunger = user.hunger - EAT * 2
user.energy = user.energy + SLEEP * 2
db.user.update(user)

# After — logic in the entity, service only persists
user.eat()
user.sleep()
user_repo.save(user)
```

Then `User.eat()` is a pure in-memory unit test. Milliseconds, no mocks, no drift.

## Property-Based Testing

For anything with a clear invariant over a large input space (parsers, encoders,
sorters, validators, state machines), use property-based tests in addition to
example tests. Libraries: `fast-check` (TS), `hypothesis` (Python), `proptest` (Rust).

Rule: if you're writing the 4th example test for the same function, switch to a property.

## Flaky Test Rules

1. Never commit a flaky test. If one lands, quarantine within 24h.
2. Quarantine means: skip with a linked issue, owner, and deadline. No owner = delete.
3. Fix flakiness at the root — never by retry loops, `sleep()`, or higher timeouts.
4. Common roots: shared global state, real clock, test ordering, unseeded randomness, network. Fix the root, not the symptom.

## Migration Rules (existing Mockist codebase)

Do not rewrite existing tests for sport. Apply incrementally:

1. **New tests** from today onward follow these rules fully.
2. **Touched files**: when editing a test, convert its mocks at the boundary only.
3. **Worst offenders first**: identify top 3-5 files with the most `toHaveBeenCalledWith` — rewrite those one domain at a time.
4. Introduce a real database (Testcontainers / docker-compose) for **one** high-risk domain first. Expand only after the pattern is proven.
5. Delete snapshot tests on non-deterministic outputs. Replace with structural assertions or delete.

## Workflow Rules

- Write the failing test from the spec **first**, then implement against it.
- Never generate code first and ask an agent to "write tests for this file" — that produces coverage theater locked to the current implementation.
- One behavior per test. If you need three `expect()` to describe one behavior that is fine; if you are testing three behaviors, split into three tests.

## PR Red Flags — Reject or Rework

- More `mock.*` calls than real assertions.
- `toHaveBeenCalledWith` / `verify()` as the only assertion.
- Imports reaching into `_internal/` or private module paths.
- Snapshots of LLM, timestamp, or network output.
- `it.skip` without a linked issue and owner.
- Tests renamed every time the function under test is renamed (leakage).
- A test file longer than the file it tests, for a file with one public function.
- New `mockall` / full-prisma-mock added instead of boundary mock or real DB.

## When NOT to Write a Test

- Plain CRUD with no logic → one E2E covers it.
- Framework wiring (DI, routing, modules) → framework tests it.
- Config / constants → type system or schema validator tests them.
- Throwaway scripts → unless they touch production data.
- Code you are about to delete.

If you cannot state the behavior the test protects in one sentence, do not write it.

## One Line to Remember

> Hide the implementation from the test. Hide the test from the implementation.
> Only behavior connects them.