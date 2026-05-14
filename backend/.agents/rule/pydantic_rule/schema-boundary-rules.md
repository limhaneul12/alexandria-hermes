# Schema Boundary Rules

## Goal

Keep schema boundaries explicit so that OMX control surfaces remain reliable, inspectable, and easy for agents to consume.

This repository is built around contracts. Schema boundaries should therefore be treated as primary design surfaces, not as incidental implementation details.

## Core Direction

- Schemas define contracts.
- Contracts should be explicit.
- Boundary ambiguity should be reduced early.
- Raw runtime payloads should not spread unchecked across the codebase.

## Scope of This Document

This document defines repository-level boundary design rules.

For Pydantic-specific modeling policy, read:
- `docs/rules/pydantic/README.md`
- especially `docs/rules/pydantic/03-boundary-normalization.md`

Use this file to decide **where boundaries exist and how they should be managed across the repository**.
Use the Pydantic rule set to decide **how schemas should model those boundaries**.
For JSON/JSONL runtime ingestion, treat raw parsing, routing, and normalization as a distinct seam that may exist before stable contract validation.

## Boundary Categories

The repository has several boundary categories. Each should be modeled intentionally.

### 1. Agent input boundary

These are inputs entering the adapter from a caller.

Examples:
- execution requests
- runtime inspection requests
- team status requests
- history search requests
- bridge/probe requests

Repository expectation:
- define the boundary explicitly,
- decide which module owns it,
- keep downstream code from guessing what the caller meant.

### 2. OMX output boundary

These are raw values coming from OMX.

Examples:
- JSON payloads
- JSONL event lines
- structured team/runtime responses
- mixed stdout/stderr payloads that are normalized into structured data

Repository expectation:
- raw OMX payloads should stop at a clear boundary layer,
- downstream modules should consume normalized contract objects rather than transport-shaped data,
- stdout/stderr and transport noise should not leak across the adapter surface.

Detailed normalization mechanics live in:
- `docs/rules/pydantic/03-boundary-normalization.md`

### 3. Adapter public output boundary

These are responses exposed by the adapter to callers.

Examples:
- normalized execution events
- runtime status snapshots
- team state results
- history search results
- probe/envelope reports

Repository expectation:
- public results should present stable meanings,
- adapter output should be easier for agents to consume than raw OMX output,
- boundary ownership should be obvious from the module layout.

### 4. Settings/config boundary

When settings need validation or structured defaults, use a typed contract surface and keep configuration interpretation out of arbitrary call sites.

## Contract Clarity Rule

Every important schema should answer:
- what does this structure represent?
- who produces it?
- who consumes it?
- what fields are required?
- what fields are optional for real contract reasons?
- what coercion or validation rules apply?
- if it is a collection, whether the collection itself owns invariants such as duplicate rejection, membership consistency, or helper behavior.

If those answers are unclear, the schema boundary is not designed clearly enough.

## Boundary Ownership Rule

Each important boundary should answer:
- which module receives the raw value?
- which module is responsible for interpreting it?
- where does transport-shaped data stop?
- where does the stable adapter contract begin?

If those answers are unclear, the boundary design is unclear.

## JSON and Transport Boundary Rule

Use `orjson` as the default JSON library for repository transport handling.

### Default stance

- Do not introduce standard-library `json` in production adapter code when `orjson` can handle the job.
- Prefer one repository-wide JSON transport choice over mixed serializer/parser habits.
- Treat raw JSON and JSONL as transport-layer concerns until routing and normalization are complete.

### Layered flow

Treat runtime JSON handling as a layered flow:
1. transport seam receives raw bytes/text/JSONL lines,
2. `orjson` parses candidate JSON units,
3. routing/normalization decides which stable contract or raw passthrough lane applies,
4. Pydantic validates only the canonical contract boundary.

This repository intentionally distinguishes:
- transport parse success,
- normalization/routing success,
- contract validation success.

Do not collapse those three checks into one implicit step in runtime/event-stream code.

### Review question

Before adding JSON handling, ask:
- Is this raw transport parsing, or is this already a stable contract boundary?

If it is raw transport parsing, use `orjson` first.

## Boundary Leakage Rule

Do not let temporary transport quirks become long-lived repository conventions.

Examples of leakage to avoid:
- raw OMX dictionaries passed through several layers,
- mixed stdout/stderr blobs treated as if they were domain objects,
- caller-facing modules depending directly on transport-specific field names.

Normalize once, then pass stable meanings forward.

## Schema Placement Rule

Keep schemas under `schemas/`.

Split them by concept using:
- `{concept}_schemas.py`

Examples:
- `execution_schemas.py`
- `runtime_schemas.py`
- `teamwork_schemas.py`
- `history_schemas.py`
- `bridge_schemas.py`

Do not centralize unrelated contracts in one giant schema file.

## Schema Growth Rule

If a concept file grows large, split by sub-concept while preserving concept ownership.

Example direction:

```text
schemas/
└── execution/
    ├── request_schemas.py
    ├── event_schemas.py
    └── result_schemas.py
```

Only do this when file size or conceptual density justifies it.

Do not over-fragment too early.

## Domain Collection Boundary Rule

Avoid raw `list[...]` at stable schema boundaries when the collection has domain meaning.

Use:

- `tuple[T, ...]` for immutable ordered sequences when duplicates are allowed and no collection-level behavior is needed;
- a `StrictRootSchemaModel` collection when the collection owns validation, helper methods, duplicate rules, membership checks, or status buckets.

Examples that should usually be root schemas rather than raw lists:

- repo/flow collections in multi-operator snapshots;
- active/launchable/resumable/cleanup/terminal flow ID collections;
- worker assignment collections derived from a Ralph PRD;
- repeated `NonEmptyString` collections that represent named domain tokens.

Root collection validators should enforce collection-level invariants instead of scattering those checks across runtime helpers.

## TypedDict Key-Presence Rule

For transport-owned or normalization-owned `TypedDict` contracts:
- keep key-presence semantics honest,
- use plain fields for all-required `TypedDict` classes,
- use plain fields inside `TypedDict(..., total=False)` when every field is optional,
- keep `Required[...]` / `NotRequired[...]` only when mixed requiredness is genuinely needed in the same `TypedDict`,
- do not force explicit key-presence wrappers when modern `TypedDict` defaults already communicate the contract clearly,
- do not over-tighten still-dynamic nested raw payloads just for style consistency,
- keep key presence separate from value nullability; a field may still be required even when its value normalizes to `None` before schema validation.

This repository prefers explicit key-presence annotations where they add real meaning, especially on stable mixed-requiredness subsets. It does not use `Required[...]` / `NotRequired[...]` as blanket style on every transport shape.

## Dynamic Boundary Rule

Some OMX surfaces may remain dynamic for practical reasons.

When that happens:
- keep the dynamic handling localized,
- document which layer is allowed to stay dynamic,
- convert to an explicit contract as soon as the structure is understood,
- do not let dynamic looseness leak into the stable adapter API,
- allow a raw passthrough lane when runtime/event-stream payloads are not yet ready for canonical schema promotion.

Detailed schema-handling guidance for this case lives in:
- `docs/rules/pydantic/03-boundary-normalization.md`

## Design Principle

Schemas are not paperwork in this repository.
They are the main mechanism that turns OMX into something agents can use safely.

A good boundary should make the adapter clearer than the raw runtime beneath it.
