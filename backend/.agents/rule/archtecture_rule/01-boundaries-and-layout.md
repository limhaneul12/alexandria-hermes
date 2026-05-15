# 01. Boundaries And Layout

## Goal

Keep the backend organized by bounded context, while avoiding both root-level sprawl and a broad shared dumping ground.

## Active Layout Rule

- `<backend_root>/` is the runtime root.
- `<shared_root>/` is the narrow shared area for code that multiple domains truly share.
- `<test_root>/` is the root test area.
- Domain-specific code belongs in bounded-context folders.
- Current active app areas are:
  - `<backend_root>/cli_support/`
  - `<backend_root>/library/`
  - `<backend_root>/mcp_server/`
  - `<backend_root>/platform/`

## Root Rule

Allowed root-level backend app files should stay small and runtime-oriented:

- `main.py`
- `container.py`
- `settings.py`
- `shared/`
- bounded-context directories

Do not place feature business logic directly in `<backend_root>/` root.

## Bounded Context Rule

Each bounded context should prefer this shape:

- `application/`
- `domain/`
- `infrastructure/`
- `interface/`
- `containers.py` when the context actually needs context-local composition

Context-local runtime helpers may also exist when the bounded context truly owns them, for example:

- `workers/` for bounded-context background workers
- `maintenance/` for bounded-context smoke or maintenance utilities

Inside the context:

- `domain/` holds entities, value objects, enums, typed contracts, and ports.
- `application/` holds use cases and policy logic.
- `infrastructure/` holds DB/cache/external integrations and repository implementations.
- `interface/` holds routers and schemas only.

## Application Scaling Rule

### Adopt now

Keep `application/` flat while the number of use cases is still small.

When it grows large enough that one flat folder becomes noisy, split by feature/use-case family.

Suggested scaling path:

- small case: `application/<feature>_usecase.py`
- larger case: `application/{feature}_usecase/`
- inside that folder, split by concrete use-case files when needed

Examples:

- `application/review_usecase.py`
- `application/review_usecase/approve.py`
- `application/review_usecase/reject.py`
- `application/review_usecase/list_pending.py`

The rule is the same as `types/` growth:

- do not over-split early
- but once the folder becomes crowded, expand by feature family instead of keeping one giant flat list

## Class Responsibility Rule

### Adopt now

Use responsibility as the primary rule and method count as a practical warning signal.

Preferred standard:

- one class should have one primary responsibility
- if the class cannot be described clearly in one sentence without "and", it is already a split candidate

Heuristic thresholds:

- review threshold: more than 8 methods in one class
- split/refactor threshold: more than 12 methods in one class

Count both public and private methods when judging class size.
Do not count `__init__` in the threshold.
Count lifecycle/helper methods other than `__init__` in the total surface.

Independent split triggers, even before method-count threshold:

- one class mixes parsing + persistence
- one class mixes orchestration + scoring/policy logic
- one class mixes read shaping + state transition logic
- one class mixes external IO + domain decision logic

Workers, repositories, and use-case classes are not exempt.

Allowed exception:

- a small orchestrator class may keep a few lifecycle/helper methods if the class still has one clear sentence-level responsibility

Current repo review target:

- classes and modules under `<backend_root>/library/` should stay split by
  search, item, prompt, skill, provider, import/export, usage, and context
  ownership instead of becoming one omnibus library manager.

Good example direction:

- `ProviderCredentialPolicy`
  - decides credential validity
  - does not persist providers or call external providers
- `LibraryItemPayloadMapper`
  - maps item models into read payloads
  - does not search, mutate status, or own provider calls

Bad example direction:

- one service that searches library items, mutates item details, calls provider
  credentials, imports archives, records usage, and shapes responses together
- one router/helper that validates request payloads, persists data, calls
  providers, and formats response DTOs together

## Shared Rule

### Adopt narrowly

`<shared_root>/` is the only allowed place for code that is truly cross-domain and not owned by one context.

Good candidates:

- shared infrastructure primitives such as SQLAlchemy `Base`
- shared infrastructure container/resources
- shared constants
- small runtime/config primitives
- backend-wide utilities under `shared/utils/` when they are truly cross-domain
- neutral infrastructure exceptions
- common container helpers truly used by multiple domains
- shared guardrails/checkers that express backend-wide architectural policy

Bad candidates:

- domain policies
- request/response schemas
- repositories query logic
- use cases
- feature helpers that only happen to be reused twice; keep those under the
  owning domain's `{domain}_utils/` folder when a utility folder is justified

## Constants Rule

### Adopt now

Prefer code-level constants over new environment variables whenever the value is:

- static for the service,
- not deployment-secret,
- not environment-specific,
- and not something operators must tune per environment.

Use environment variables only for real deployment/runtime variability such as:

- secrets
- connection targets
- credentials
- externally supplied toggles

Do not create environment variables for values that should be stable product or domain constants.

## Repositories Rule

- Repository interfaces/ports are standardized under `<backend_root>/<domain>/domain/repositories/`.
- These are interfaces/contracts only.
- Concrete repository implementations belong under `<backend_root>/<domain>/infrastructure/repositories/`.
- Do not mix repository contracts and repository implementations in the same layer.
- Do not use shared repositories as a shortcut for unrelated query families.
- Existing singular `repository/` folders are legacy and should not be used for new backend work.

## Exception Rule

### Adopt narrowly

Do not introduce a big exception taxonomy up front.

Current repo rule:

- keep one discoverable exception catalog under `<shared_root>/exceptions/`
- domain-specific failures live in domain-scoped modules such as
  `library_exceptions.py` and `cli_exceptions.py`
- exception class names must stay domain-scoped, for example
  `LibraryProviderConfigError`
- only truly cross-domain route/runtime/stream contracts belong in neutral shared modules such as `route_exceptions.py`, `stream_exceptions.py`, and `common_exceptions.py`

Do not create `<backend_root>/<domain>/exceptions/` for new backend work unless the exception policy is deliberately changed across the backend rule set.
