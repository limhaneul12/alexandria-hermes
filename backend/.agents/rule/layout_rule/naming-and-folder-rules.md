# Naming Rules

## Goal

Use names that communicate purpose, role, and concept boundaries clearly so that the adapter remains understandable as it grows.

This repository is a contract-heavy runtime adapter. Naming should reduce ambiguity, avoid technical catch-all buckets, and make it obvious what a file or module is responsible for.

## Core Direction

- Prefer names that describe **purpose and role**.
- Avoid names that only describe **implementation mechanism**.
- Keep naming consistent across schemas, exceptions, enums, parsing, and runtime modules.
- Favor concept-split files over giant catch-all files.

## Repository Identity Rule

The repository name already carries the project identity: `omx-agent-adapter`.

Because of that:
- do not repeat the repository identity unnecessarily inside every module name,
- do not create redundant names such as `omx_agent_adapter_runtime.py`,
- do not add project-prefix noise where directory context already provides it.

Context should do part of the naming work.

## Directory Naming Rule

Use directory names for **concept or responsibility boundaries**.

Examples of good top-level source directories:
- `execution/`
- `runtime/`
- `teamwork/`
- `history/`
- `bridge/`
- `parsing/`
- `schemas/`
- `shared/`

Directory names should help a reader answer:
- what problem space is this code about?
- what kind of responsibility lives here?

## `__init__.py` Rule

Do **not** create `__init__.py` files by default.

This repository treats `__init__.py` as an exception-only file, not a routine scaffolding file.

### Default stance

- `__init__.py` should be absent unless there is a concrete reason to add it.
- Avoid sprinkling `__init__.py` files across the tree just because Python projects often do that.
- Unnecessary `__init__.py` files increase file noise and reduce structural clarity.

### Allowed uses

Only add `__init__.py` when it is truly needed, for example:
- explicit package export control is required,
- a package-level import surface is intentionally being defined,
- Python packaging/runtime behavior genuinely depends on it,
- tooling compatibility has been verified to require it.

### Review question

Before adding `__init__.py`, ask:
- What exact problem does this file solve here?

If that answer is vague, do not add it.

## File Naming Rule

### Default pattern

Prefer file names that answer:
- what concept does this file belong to?
- what role does this file play inside that concept?

Good direction:
- `runtime_snapshot.py`
- `event_feed.py`
- `payload_transport.py`
- `contract_promotion.py`
- `command_blueprint.py`
- `session_lookup.py`
- `target_probe.py`

### Avoid overly generic filenames

Avoid broad technical bucket names at arbitrary locations such as:
- `enums.py`
- `types.py`
- unqualified `utils.py`
- `helpers.py`
- `common.py`
- `models.py`
- `schema.py`
- `status.py`
- `stream.py`

These names usually become ambiguous or overloaded as the project grows.

### Avoid standard-library or popular-package collision names

Do not create filenames that can easily collide with Python modules or common libraries.

Avoid names such as:
- `enum.py`
- `typing.py`
- `types.py` when avoidable
- `pydantic.py`
- `json.py`
- `pathlib.py`
- `pandas.py`

If a concept naturally wants one of these names, prefer a purpose-qualified name instead.

Examples:
- use `runtime_enums.py` instead of `enums.py`
- use `execution_types.py` instead of `types.py`
- use `payload_json.py` only if the role is specifically JSON payload handling

### Utility placement

Utility code is allowed when it has clear ownership.

- backend-wide reusable utilities belong under `shared/utils/`.
- domain-local utilities belong under a domain-owned folder named
  `{domain}_utils/`.
- utility files inside those folders should still be named by purpose, not as a
  catch-all `utils.py` or `helpers.py`.

Examples:

```text
shared/
└── utils/
    └── string_normalization.py

library/
└── library_utils/
    └── payload_merge.py
```

Do not promote a helper to `shared/utils/` just because it is reused twice.
Promote it only when the behavior is genuinely backend-wide and not owned by a
single domain.

## Concept-Split Rule

When a kind of artifact should be grouped by category, keep similar things together **and** split them by concept.

The structures below are examples. Follow the nearest existing concept-owned
path in the current slice instead of forcing a hard-coded directory layout.

### Enums

Keep enums with enums.

Preferred cross-cutting structure:

```text
shared/
└── omx_enums/
    ├── runtime_enums.py
    ├── execution_enums.py
    ├── teamwork_enums.py
    ├── history_enums.py
    └── bridge_enums.py
```

For feature-local enums, prefer the feature's existing enum path such as
`domain/event_enum/{concept}_enums.py`.

### Exceptions

Keep cross-cutting exceptions under `shared/exceptions/`.

Preferred structure:

```text
shared/
└── exceptions/
    ├── runtime_exceptions.py
    ├── execution_exceptions.py
    ├── teamwork_exceptions.py
    ├── history_exceptions.py
    └── bridge_exceptions.py
```

### Schemas

Keep schemas with schemas.

Preferred local or cross-cutting structure:

```text
schemas/
├── runtime_schemas.py
├── execution_schemas.py
├── teamwork_schemas.py
├── history_schemas.py
└── bridge_schemas.py
```

For backend I/O schemas, prefer the existing boundary path such as
`interface/schemas/{concept}/...`.

### Types

If shared types or aliases stay small, one `types.py` may be temporarily acceptable inside a tightly scoped directory.

If the type surface grows, prefer:

```text
types/
├── runtime_types.py
├── execution_types.py
├── teamwork_types.py
└── bridge_types.py
```

The larger the project becomes, the less acceptable a single giant `types.py` file becomes.

## Shared Rule

A `shared/` directory is allowed when it contains genuinely cross-cutting definitions.

But `shared/` must not become a junk drawer.

Bad direction:
- `shared/enums.py`
- `shared/utils.py`
- `shared/helpers.py`
- `shared/misc.py`

Good direction:
- `shared/omx_enums/runtime_enums.py`
- `shared/omx_enums/execution_enums.py`
- `shared/utils/string_normalization.py`
- future concept-split shared helpers only when they are truly cross-cutting and intentionally named

## Comment and Docstring Rule

Comments are allowed, but they are not the default explanation mechanism.

### Default stance

- Prefer expressive names, explicit schemas, and small functions before adding comments.
- Do not add comments that merely restate what the code already says.
- Avoid noisy inline commentary that turns the file into narration.

### Good comment cases

Use a short comment only when it communicates something the code itself cannot make obvious quickly, such as:
- a boundary exception,
- a transport quirk,
- a non-obvious normalization rule,
- a compatibility workaround,
- a deliberate deviation from an otherwise normal repository rule.

### Docstring direction

- Public CLI commands, public-facing adapter entrypoints, and custom exceptions may use short docstrings.
- Keep docstrings concise and factual.
- Use the project docstring format from
  `backend/.agents/rule/archtecture_rule/05-type-and-schema-rules.md` when a
  docstring is present.
- Start with a short summary line ending in punctuation that explains what the function does.
- Leave one blank line between the summary and any section blocks.
- Default section labels are `Args:` and `Return:`.
- `Returns:`, `Yields:`, and `Raises:` are allowed when they are semantically
  needed or when matching an existing public surface.
- Do not write essay-style docstrings for straightforward internal helpers.

### Review questions

Before adding a comment or docstring, ask:
- Does this explain *why* or an important constraint, rather than just *what*?
- Would better naming remove the need for this comment?
- Is this boundary/quirk important enough that a future agent might otherwise make the wrong change?

If the answer is no, skip the comment.

## Naming Review Questions

Before adding a new file or module, ask:

1. Does the directory already provide enough context so I can keep the filename short?
2. Does the filename describe purpose, not just technology?
3. Could this name become ambiguous once the project doubles in size?
4. Could this name collide with a standard library module or popular package?
5. Should this be split by concept instead of appended to a generic bucket file?

If any answer is uncomfortable, rename before the file becomes entrenched.

## Design Principle

Naming should make the adapter easier to navigate than the raw OMX surface.

That means:
- concept boundaries should be visible,
- technical categories should stay organized,
- filenames should remain purpose-driven,
- and generic bucket files should be treated as a smell once the project grows.
