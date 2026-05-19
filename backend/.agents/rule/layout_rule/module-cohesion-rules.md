# Module Cohesion Rules

## Goal

Keep backend modules easy to search, reason about, and refactor by splitting by
owned concept instead of by convenience buckets.

This file owns cohesion and split guidance only. Type modeling policy lives in
`backend/.agents/rule/type_enum_rule/type-development-rules.md`, and Pydantic
boundary policy lives in `backend/.agents/rule/pydantic_rule/`.

## Core Direction

- A module should have one clear reason to change.
- A class should have one primary responsibility that can be described without
  "and".
- Split by business/concept ownership before creating broad utility buckets.
- Prefer deleting thin compatibility wrappers once callers can use the real
  concept-owned path.

## Module Split Rule

Treat a module as a split candidate when any of these are true:

- it mixes external I/O, persistence, mapping, and domain decisions;
- it has several unrelated groups of private helpers;
- new changes repeatedly touch different conceptual sections of the same file;
- a future reader cannot find the owned behavior by filename alone;
- the file is growing because it became the easiest place to add code.

Line count is only a review signal, not a hard rule. Generated files,
well-documented transport tables, and compact schema collections can be larger
when the concept is still cohesive.

## Class Cohesion Rule

Use method count as a warning signal, not a mechanical rejection rule.

Review a class when:

- it has more than roughly 8 non-dunder methods;
- it mixes parsing + persistence;
- it mixes provider/external I/O + domain decisions;
- it mixes read shaping + state transitions;
- it needs an unclear name such as `Manager`, `Handler`, or `Service` because it
  owns too many concerns.

Split/refactor when the responsibility sentence is no longer clear.

## Utility Placement Rule

Use utilities only when the helper's ownership is clear.

- Cross-domain reusable helpers belong under `backend/app/shared/utils/`.
- Domain-local helpers belong under the owning domain's `{domain}_utils/` folder
  or a more specific concept folder.
- If a helper is only used by one concept, keep it near that concept and give
  the file a purpose-specific name.

Avoid dumping unrelated helpers into `utils.py` or broad helper modules.

When several utility functions share the same request context, payload, or
configuration parameters, prefer a small purpose-named class over repeating the
same arguments through many functions. Use the constructor for the common state,
keep the class responsibility narrow, and keep the public method surface small
(roughly five methods or fewer). Do not convert such helpers to dataclasses
unless the object is primarily a value/result DTO.

## Single-File Directory Rule

Avoid creating a directory that contains only one production Python module when
the directory is merely a convenience wrapper around that module.

Preferred direction:

- flatten one-file utility/plumbing directories into a clearly named module;
- keep concept directories only when they are real architectural boundaries or
  already contain multiple cohesive modules;
- when one module becomes too large for one clear responsibility, split it into
  a folder with multiple purpose-named modules.

Acceptable single-file boundary folders include stable architecture seams such
as repository implementations, concept-owned schema boundaries, and domain enum
or type locations when the surrounding layer expects those paths. Do not flatten
those solely for tidiness if doing so would weaken boundary clarity.

## Enum, Type, and Constant Location Rule

Stable field-name sets, enum-like strings, detail-field lists, and dispatch
registries belong near the concept that owns them.

Use shared enum/type modules only when the value set is genuinely cross-cutting.
Do not force a hard-coded example path when the current slice already has a
clearer local path.

## Return Style Rule

Named local returns are helpful when they clarify a transformation result, but
are not mandatory for trivial expressions.

Prefer named returns for:

- multi-step normalization;
- validation decisions;
- payload assembly;
- computations where the returned meaning is otherwise unclear.

Direct returns are fine for obvious passthroughs or single-expression helpers.
Do not add local variables just to satisfy style.

## Async Boundary Rule

Keep pure transformation/schema logic synchronous by default. Introduce `async`
only where the function actually awaits external I/O, subprocesses, streams, or
other async resources.

When bridging blocking code, prefer a thin async boundary over spreading async
through deterministic helpers.

## Review Questions

Before adding to an existing module, ask:

1. Is this the concept-owned place for the behavior?
2. Would a filename search lead future agents here?
3. Is the helper reusable across domains, domain-local, or concept-local?
4. Is this file growing because of cohesion, or because it is convenient?
5. Can a smaller module name make the responsibility obvious?
