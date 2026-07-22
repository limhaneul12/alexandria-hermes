# Alexandria-Hermes Agent Entry

This file is the mandatory entrypoint for agents modifying the Alexandria-Hermes backend.

Before modifying backend code, read the following files in order:

1. `.agent/docs/ruls/규칙.md`
2. `.agent/docs/ruls/README.md`
3. The detailed rule documents directly related to the current task
4. Any PRD, meeting note, or requirements document explicitly designated for the current task

The source of truth for backend development rules is:

```text
.agent/docs/ruls/
```

PRDs, meeting notes, and functional requirements are not development rules.

Do not automatically treat an attached or discovered PRD as an implementation request. Use it as task input only when the user explicitly requests its application or the repository explicitly links it to the current task.

When repository conventions and a task-specific document conflict, do not silently choose one. Identify the conflict before expanding the change scope.

---

# Project Structure and Module Organization

This repository is a backend and CLI service for Alexandria-Hermes.

## Repository Structure

* `backend/`

  * Python FastAPI service with CLI and MCP integration
  * `backend/AGENTS.md`

    * Mandatory backend agent entrypoint
  * `backend/.agent/docs/ruls/`

    * Source of truth for backend development rules
  * `backend/app/`

    * Backend application code
    * Application entrypoint: `backend/app/main.py`
  * `backend/app/platform/`

    * Platform-level concerns such as routing, middleware, lifecycle, configuration, and logging
  * `backend/app/shared/`

    * Definitions and guardrails genuinely reused across multiple concepts
    * Must not become a generic utility bucket
  * `backend/tests/`

    * Backend tests named `test_*.py`
* `docker-compose.yml`

  * Runs the backend service only
* `README.md`

  * High-level setup and startup instructions

The previous Next.js `frontend/` service has been removed.

Do not add npm, Node.js, React, Next.js, or frontend workflows unless the product direction changes explicitly.

Preserve the existing Alexandria-Hermes directory structure unless the current task provides a concrete reason to change it.

Do not create generic modules or directories such as:

* `util`
* `utils`
* `helpers`
* `common`
* `misc`

Prefer purpose-specific names such as:

* `frontmatter_parser.py`
* `scope_identity_validator.py`
* `context_recall_filter.py`
* `compact_promotion_service.py`
* `graph_edge_indexer.py`

---

# Build, Test, and Development Commands

## Required Rule Reading

Before changing backend code, read:

1. `AGENTS.md`
2. `.agent/docs/ruls/규칙.md`
3. `.agent/docs/ruls/README.md`
4. The detailed rule documents relevant to the current task
5. Task-specific documents explicitly designated by the user or repository

Do not read every detailed rule file automatically when only a subset is relevant.

## Backend Commands

Run backend commands from the `backend/` directory.

```bash
cd backend
uv sync
uv run ruff check .
uv run ruff format .
uv run pyrefly check
uv run pytest -q
```

A backend change is not `VERIFIED` unless the relevant formatting, linting, type checking, and tests have actually completed successfully.

When only part of the verification suite was executed, report:

* The exact commands executed
* Their exit status
* The scope actually verified
* Any checks that were not executed

Do not report `VERIFIED` merely because tests were written or code was reviewed statically.

## Service

From the repository root:

```bash
docker compose up --build
```

The backend service starts on:

```text
127.0.0.1:8000
```

Local liveness endpoint:

```text
http://localhost:8000/health/live
```

---

# Coding Style and Contract Conventions

Python targets version `3.13`, as defined in `pyproject.toml`.

Use the repository Ruff configuration.

Default formatting conventions:

* 88-character line length
* 4-space indentation
* Double quotes
* Explicit absolute module paths such as `app.platform...`
* Explicit parameter and return types on production public functions

## Model Responsibilities

Use each model type for its intended responsibility.

```text
FastAPI, MCP, JSON, YAML, file, and frontmatter validation boundaries
→ Pydantic v2 models

Validated internal service and repository DTOs
→ Frozen dataclasses

Known raw or partial mapping shapes
→ TypedDict

Database persistence
→ SQLAlchemy models

Truly dynamic JSON transport values
→ Narrowly scoped JsonValue-style types
```

Do not convert every internal object to Pydantic.

Do not replace SQLAlchemy persistence models with Pydantic models.

Do not create a corresponding dataclass for every Pydantic model unless the external contract and internal representation have genuinely different responsibilities.

## Internal Dataclass DTOs

Validated internal DTOs should normally use:

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextIdentity:
    workspace_id: str
    project: str
    agent_id: str | None
    session_id: str | None
```

Use internal dataclasses for:

* Service-to-repository values
* Validated snapshots
* Search candidates
* Mapping results
* Internal commands and results
* Values whose main responsibility is not runtime validation or serialization

Mutable dataclasses are allowed only when mutation represents a real responsibility, such as:

* Reindex counters
* Stream accumulators
* Batch assembly state

Document why a mutable dataclass is necessary.

Do not move substantial external-input validation into dataclass `__post_init__`.

External values should be validated at the Pydantic boundary before an internal DTO is created.

## Dictionary Policy

Do not pass known structures through production code as:

```python
dict[str, Any]
dict[str, object]
```

Use:

* Pydantic for runtime validation
* Dataclasses for validated internal DTOs
* TypedDict for known raw or partial mapping shapes
* SQLAlchemy models for persistence
* Enums or literals for constrained protocol values

TypedDict describes a mapping shape but does not perform runtime validation.

Raw external mappings must be normalized and validated before entering core application services.

Do not use `cast(...)` to treat an unvalidated dictionary as a known structure.

## TypedDict Key Semantics

Distinguish key omission from nullable values.

```text
Optional key
→ NotRequired[T]

Required key with nullable value
→ T | None

Optional key with nullable value
→ NotRequired[T | None]
```

Example:

```python
from typing import NotRequired, TypedDict


class PartialFrontmatter(TypedDict):
    project: NotRequired[str]
    agent_id: NotRequired[str | None]
```

Use `Required` and `NotRequired` only when mixed key presence carries real meaning.

## Type Strictness

`Any` is prohibited by default in production code.

It may be used only at unavoidable dynamic boundaries, such as:

* Untyped third-party libraries
* Initial JSON or YAML parsing
* Dynamic MCP or plugin transport
* Framework hooks with incomplete typing

When `Any` is unavoidable:

* Keep it inside the boundary function or module.
* Document why it is required.
* Convert it promptly to a TypedDict, Pydantic model, dataclass, enum, or another explicit type.
* Do not expose it through core service or repository public APIs.

Do not use `dict[str, object]` as a substitute for designing an explicit type.

Use `T | None` only when `None` is a valid state in the contract.

Do not make required values optional merely to:

* Simplify construction
* Avoid validation
* Suppress type errors
* Delay a design decision
* Treat empty strings and `None` as equivalent

Avoid broad unions such as:

```python
str | int | dict | list | None
```

outside raw transport boundaries.

Prefer:

* Enums
* Literals
* Discriminated unions
* Named Pydantic models
* Named dataclasses
* TypedDict definitions

Broad `type: ignore`, `# noqa`, unchecked casts, and type-checker configuration weakening are prohibited.

If suppression is unavoidable, keep it narrow and document the exact reason.

## Collections

Use collection types according to their behavior.

* Immutable ordered sequence: `tuple[T, ...]`
* Intentionally mutable sequence: `list[T]`
* Unique-value collection: `set[T]`
* Read-only mapping input: `Mapping[K, V]`
* Intentionally mutable mapping: `dict[K, V]`

Do not use mutable collections merely because they are easier to construct.

## Pydantic Rules

Use Pydantic v2 APIs:

* `model_validate(...)`
* `model_validate_json(...)`
* `model_dump(...)`
* `model_dump_json(...)`

Use validation APIs for raw or untrusted values.

```python
request = ContextCreateRequest.model_validate(raw_payload)
```

Use normal constructors with explicit keyword arguments for trusted internal values.

```python
result = ContextCreateResult(
    context_id=context_id,
    status=status,
)
```

Do not use `model_validate({...})` as a convenience wrapper around a dictionary created from already typed local values.

Stable named-field boundary contracts should generally use:

```python
ConfigDict(
    extra="forbid",
    frozen=True,
    validate_default=True,
)
```

Do not enable the following globally without a specific contract reason:

* `strict=True`
* `use_enum_values=True`
* `validate_assignment=True`
* `str_strip_whitespace=True`
* `populate_by_name=True`
* `arbitrary_types_allowed=True`
* `from_attributes=True`

Use `RootModel` only when the root value itself is the contract.

Examples include:

* A domain-specific ID collection
* A collection with duplicate rejection
* A collection that owns membership or consistency invariants

Do not use `RootModel` as the default shape for ordinary named-field contracts.

## Frontmatter Validation

Raw Obsidian frontmatter may contain:

* Legacy fields
* User-defined metadata
* Fields from older Alexandria-Hermes versions

Do not automatically apply the same `extra="forbid"` policy used for stable API requests.

Use an explicit flow:

```text
Raw YAML mapping
→ TypedDict or restricted raw mapping
→ Known-field normalization
→ Pydantic canonical validation
→ Internal dataclass DTO
```

Unknown fields must be handled through an explicit policy such as:

* Preserve
* Collect as extensions
* Warn
* Send for review
* Reject

Do not silently delete unknown metadata.

## Defaults and Nullability

Defaults must represent real protocol or domain defaults.

Do not add defaults merely to make object construction easier.

Do not hide missing data with expressions such as:

```python
value or {}
value or []
value or ""
```

If fallback behavior is part of the contract, implement it in a named normalizer and test it explicitly.

---

# Naming Conventions

Use:

* `snake_case` for functions and variables
* `PascalCase` for classes
* Purpose-specific module and class names
* Question-like names for Boolean values

Good examples:

* `ScopeIdentityValidator`
* `FrontmatterContextMapper`
* `ContextRecallFilter`
* `ObsidianReindexService`
* `validate_scope_identity`
* `parse_frontmatter`
* `filter_recall_candidates`
* `is_current`
* `has_errors`
* `can_promote`

Avoid vague names such as:

* `Manager`
* `Helper`
* `Util`
* `Processor`
* `CommonService`
* `handle`
* `process`
* `do_work`
* `convert_data`

A general term is acceptable only when its concrete responsibility is obvious from the complete name.

Do not use abbreviations such as `ctx`, `obj`, `tmp`, or `mgr` on public surfaces unless the abbreviation is an established domain term.

---

# Class, Function, and Module Cohesion

## Classes

A class should own one cohesive responsibility.

Do not combine the following in one class without a concrete reason:

* Parsing
* Validation
* Persistence
* Search
* Lifecycle management
* Orchestration
* Report rendering

A class should normally expose no more than six behavioral methods.

The following do not normally count toward that limit:

* `__init__`
* Clear dunder methods
* Simple read-only properties
* Framework-required hooks

When a class exceeds six behavioral methods, review whether its responsibilities should be separated into concepts such as:

* Parser
* Validator
* Mapper
* Repository
* Builder
* Service
* Orchestrator

If retaining the larger class is justified, document the reason briefly in the class docstring.

Do not create a `Manager` class that owns filesystem operations, database operations, search, validation, lifecycle, logging, and reporting together.

## Modules

A module exceeding roughly 430 lines is a review trigger, not an automatic split requirement.

Split it only when doing so improves:

* Responsibility boundaries
* Type clarity
* Testability
* Dependency direction
* Navigation

Generated code, declarative mappings, and clearly cohesive modules may exceed the review threshold.

## Functions

Functions should perform one clear operation.

Review a function for separation when:

* Its name requires “and.”
* Validation and side effects are mixed.
* Raw parsing and canonical object construction happen together.
* It contains several unrelated recovery paths.
* Its return type becomes overly broad.
* It contains deeply nested branching.

Prefer meaningful named local values in validation, transformation, and aggregation code before returning the result.

Direct expression returns are acceptable for trivial passthroughs where they are clearer.

## Imports

Production imports belong at module scope by default.

Do not use local imports as a normal solution to circular dependencies.

Refactor the dependency boundary first.

Keep a local import only when an external or runtime boundary makes it genuinely unavoidable, and document the reason.

---

# Docstring Conventions

Use concise Google-style docstrings when a public function, CLI command, MCP tool, or custom exception benefits from documentation.

Use the exact section names:

* `Args:`
* `Returns:`
* `Yields:`
* `Raises:`

Use `Returns:`, not `Return:`.

Document what parameters and return values mean, not merely their names and types.

Do not add docstrings that only repeat:

* The function name
* The type annotations
* Obvious implementation details

---

# Architecture and Boundary Rules

Use the following dependency direction unless the existing implementation provides a justified alternative:

```text
FastAPI Router or MCP Tool
→ Pydantic input contract
→ Application service
→ Internal dataclass DTO or domain operation
→ Repository, Obsidian, or search adapter
→ Pydantic output contract
```

## Routers

Routers should handle:

* External input
* Boundary validation
* Request context
* Application service invocation
* Structured responses

Routers should not own:

* Core lifecycle rules
* Scope and identity invariants
* SQL query construction
* Frontmatter parsing
* Search aggregation
* Recovery algorithms
* Direct multi-step file transitions

## Services

Application services should own:

* Use-case coordination
* Post-validation business invariants
* Lifecycle transitions
* Idempotency
* Repository coordination
* Structured operation results

Services should not depend directly on FastAPI request objects.

## Repositories

Repositories should own persistence and retrieval.

Repositories should not:

* Decide unrelated business policy
* Construct router responses
* Return transport-shaped raw dictionaries to upper layers
* Hide failed persistence behind empty results

## Mappers

Pydantic, dataclass, SQLAlchemy, and frontmatter representations should be converted by named, concept-owned mappers when a conversion boundary is genuinely required.

Examples:

* `ContextRequestMapper`
* `ContextEntityMapper`
* `FrontmatterContextMapper`

Do not scatter `model_dump()` plus `**kwargs` conversions throughout the codebase.

---

# Storage and Index Rules

Obsidian Markdown is the canonical storage layer.

SQLite, FTS, Vector, Embedding, and Graph structures are rebuildable indexes or read models.

Do not assume that a SQLite transaction and filesystem changes form one atomic transaction.

Canonical write operations should generally follow this sequence:

```text
Validate
→ Build validated internal DTO
→ Write temporary Markdown file
→ Atomic filesystem replace
→ Read-back verification
→ Update indexes
→ Verify index state
→ Produce a structured result or report
```

If the Markdown write succeeds but an index update fails:

* Do not automatically delete the canonical Markdown.
* Record a structured index error.
* Preserve enough information for reindex recovery.
* Prevent invalid or incomplete index state from appearing as a normal recall result.

Reindex operations should support structured reporting, including relevant values such as:

* Scanned notes
* Indexed notes
* Updated notes
* Skipped notes
* Stale notes
* Error notes
* Duration
* Run ID

Do not let one malformed note silently invalidate all correctly formed notes.

Tests must not modify, delete, or rebuild the user’s actual Obsidian vault.

Use:

* Temporary vaults
* Fixture vaults
* Temporary SQLite databases
* Isolated index directories

Keep SQLAlchemy models as persistence models.

Do not globally enable `from_attributes=True` merely to couple ORM entities directly to public API models.

---

# Async and I/O Rules

Keep the following logic synchronous by default:

* Validation
* Mapping
* Normalization
* Hashing
* Filtering
* Schema construction
* Lifecycle decisions

Use async only at real I/O boundaries, such as:

* HTTP calls
* MCP remote calls
* Subprocesses
* Stream ingestion
* Async database drivers
* External file watchers

Do not spread async through deterministic internal helpers.

Do not run blocking filesystem or blocking-library operations directly inside async endpoints.

Use the repository’s existing async-boundary abstraction. If none exists, use a narrow, explicit boundary such as `asyncio.to_thread(...)` when justified.

Use task groups only for genuinely independent concurrent I/O.

Do not add concurrency around sequential validation, schema construction, or deterministic transformations.

---

# Error and Exception Rules

External boundaries should return structured errors.

Include relevant values such as:

* `error_code`
* `message`
* `operation`
* `resource_id`
* `note_path`
* `recoverable`
* `run_id`
* `details`

Keep exceptions concept-specific.

Examples:

* `context_exceptions.py`
* `obsidian_exceptions.py`
* `search_exceptions.py`
* `librarian_exceptions.py`

Do not put all repository exceptions in a single generic file unless the existing structure provides a strong reason.

Use `except Exception` only at explicit boundary or recovery layers.

When catching a broad exception:

* Convert it into a structured failure
* Re-raise it with relevant context
* Record an auditable failure state
* Or perform an explicit recovery action

Do not silently ignore exceptions.

Distinguish:

* Pydantic validation errors
* Domain invariant errors
* Persistence errors
* Index errors
* External dependency errors

Do not convert every error into HTTP 500.

Never include secrets, passwords, tokens, or raw credentials in exception messages, logs, frontmatter, test fixtures, or operation reports.

---

# Testing Guidelines

The backend test framework is `pytest`.

Tests are discovered under:

```text
backend/tests/
```

Test files must be named:

```text
test_*.py
```

Before review, run:

```bash
uv run pytest -q
```

Tests should be:

* Fast
* Deterministic
* Isolated
* Independent of external services in the default suite
* Independent of the user’s actual Obsidian vault
* Explicit about temporary file and database cleanup

Test convenience must not weaken production types or contracts.

Before modifying behavior, run relevant existing tests to establish a baseline.

Classify failures as:

* Pre-existing
* Change-induced
* Environment-related
* Flaky

A test that was written but not executed is not verification evidence.

---

# Commit and Pull Request Guidelines

Use the Lore commit protocol defined by the repository root runtime instructions.

Keep development-rule changes separate from functional behavior changes when practical.

Pull requests should include:

* Concise summary
* Impacted areas
* Commands actually run
* Formatting, lint, typecheck, and test results
* Known failures
* Risk notes
* Rollback notes when changing lifecycle, storage, indexing, configuration, or logging behavior

Do not describe code as verified when the required commands were not executed successfully.

---

# Security and Configuration

Runtime configuration is environment-based.

* Application configuration uses the `SERVICE_` prefix.
* Stream configuration uses the `STREAM_` prefix.
* Local secrets belong only in local environment files.
* Never commit credentials, tokens, passwords, or private keys.
* Do not include secrets in logs, exceptions, frontmatter, test fixtures, or evidence artifacts.

Keep the backend bound to local interfaces unless broader exposure is explicitly required.

---

# Agent Execution Rules

Use one clear goal per run.

Do not interpret the existence of a PRD as permission to implement all of it.

Before modifying code:

1. Read the mandatory development rules.
2. Read only the detailed rules relevant to the task.
3. Read task-specific documents explicitly designated by the user or repository.
4. Inspect the current implementation.
5. Inspect relevant existing tests.
6. Identify expected changed files.
7. Identify public contract, migration, storage, and compatibility impact.
8. Discover the repository’s actual verification commands.

Do not:

* Create new abstractions without inspecting existing implementations.
* Expand the task merely to apply every repository rule.
* Perform repository-wide cleanup during a focused feature change.
* Hide failed or unexecuted tests.
* Claim that code existence proves completion.

Report work using one of the following states:

* `DISCOVERED`
* `PLANNED`
* `IMPLEMENTED`
* `VERIFIED`
* `BLOCKED`

Use `VERIFIED` only when the required commands and acceptance tests actually passed.
