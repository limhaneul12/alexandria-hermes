# Type Development Rules

## Goal

Keep production source code strongly typed, explicit, and predictable so that the adapter remains trustworthy as an agent-facing OMX control surface.

This repository is contract-heavy. Type discipline is therefore a design rule, not an optional cleanup concern.

## Core Direction

- Treat types as a first-class design concern.
- Missing or incorrect types in production source code are real defects.
- Prefer explicit contracts over loosely typed dictionaries or implicit conventions.
- Optimize for agent-facing runtime contracts, not backend-style domain modeling.

## Source of Truth Split

Detailed Pydantic-specific policy lives under:
- `docs/rules/pydantic/README.md`

Detailed boundary and transport-seam policy lives under:
- `docs/rules/schema-boundary-rules.md`

Use the Pydantic rule set for:
- schema design
- `ConfigDict` decisions
- `BaseModel` vs `RootModel` decisions
- strictness/default/nullability decisions
- contract modeling after routing/normalization
- enum/literal/shared-type decisions related to schema contracts

Use the boundary rule set for:
- transport parsing ownership
- JSON/JSONL seam policy
- routing/normalization ownership
- raw passthrough decisions

## Production Typing Rule

- Public adapter surfaces should be explicitly typed.
- Avoid pushing `dict[str, Any]` through the core adapter surface.
- Avoid broad `dict[str, object]` in production source unless the dynamic boundary truly requires it.
- If a raw dictionary shape must remain, keep it localized to the parsing/normalization seam and add a short justification comment explaining why a stronger contract is not yet justified.
- Avoid broad `Any` unless the dynamic boundary truly requires it.
- If a runtime seam is inherently dynamic, localize that looseness to parsing/normalization boundaries and convert to explicit contracts quickly.

## Source vs Test Rule

- Production `src/` code should be held to a stricter standard than tests.
- Tests can be somewhat more flexible, but should not drive weak typing into production code.

## Pyrefly Rule

Pyrefly is the canonical static type checker for production source code in this repository.

Current direction:
- source code should stay type-clean under Pyrefly,
- production `src/` code should remain stricter than tests,
- do not silence type issues casually,
- do not use broad casts or `Any` as the first escape hatch.

## Return Style Rule

- Production source should prefer returning named local variables over direct expression returns.
- Especially in validation, normalization, transformation, and aggregation code, assign the final value to a clearly named variable before returning it.
- Use the variable name to make the returned meaning obvious to a future reader or agent.
- Trivial passthroughs may be tolerated, but named returns are the default preference.

## Async Boundary Rule

- Keep core transformation and schema logic synchronous by default.
- Introduce `async` only at real boundary points where the code waits on external I/O, subprocess execution, or stream ingestion.
- Prefer a thin async entrypoint over spreading `async` through pure helpers.
- When bridging existing blocking code, prefer `asyncio.to_thread(...)` at the boundary instead of rewriting pure internals into coroutine-style code.
- Do not convert small deterministic helpers to `async` unless they actually await something meaningful.
- If a function becomes async, add or update tests so the async contract is explicit.

Examples of good async candidates in this repo:
- OMX subprocess/status invocation boundaries
- execution event-stream ingestion boundaries

Examples that should usually remain sync:
- payload normalization
- schema promotion
- anomaly assembly
- small parsing helpers with no external wait state

## Module and Class Cohesion Rule

- Runtime files should be split by concept/responsibility before they become omnibus control surfaces.
- A runtime module that grows past roughly 430 lines should be treated as a refactor trigger unless it is generated code or a deliberately documented transport table.
- Do not keep thin compatibility facades for unused internal modules. Move callers to the concept-owned module path in the same slice and delete the wrapper so cleanup is not done twice.
- Move source reads, builders, classifiers, decisions, and summaries into concept-specific modules or subfolders when a folder becomes crowded.
- Classes should group one cohesive behavior and normally expose no more than 6 methods. Split token normalization, snapshot classification, builders, and orchestration into separate classes/modules instead of making one manager class absorb everything.
- Stable field-name sets, runtime marker tables, enum-like string markers, and dispatch registries belong in `adapter_types/type_contract/` or shared enum classes, not inline in runtime/control modules.
- Do not create re-export bucket packages or marker-only `__init__.py` files to hide large modules; split the actual implementation files.

## Design Principle

This repository should prefer one explicit, strongly typed contract language and a predictable static type discipline.

The detailed contract language rules are defined in the Pydantic rule set.
The broader repository typing policy is defined here.
