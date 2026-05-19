# Type Development Rules

## Goal

Keep production source code strongly typed, explicit, and predictable so that
the backend remains trustworthy as an agent-facing service.

This repository is contract-heavy. Type discipline is therefore a design rule, not an optional cleanup concern.

## Core Direction

- Treat types as a first-class design concern.
- Missing or incorrect types in production source code are real defects.
- Prefer explicit contracts over loosely typed dictionaries or implicit conventions.
- Optimize for agent-facing runtime contracts and backend domain clarity.

## Source of Truth Split

Detailed Pydantic-specific policy lives under:
- `backend/.agents/rule/pydantic_rule/README.md`

Detailed boundary and transport-seam policy lives under:
- `backend/.agents/rule/pydantic_rule/schema-boundary-rules.md`

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

- Public backend surfaces should be explicitly typed.
- Internal object DTOs should be dataclasses unless another explicit contract
  type is more appropriate.
- I/O boundary DTOs should be Pydantic v2 schemas.
- Stable dictionary payload contracts should be `TypedDict` rather than broad
  dictionaries.
- Construct `TypedDict` payloads with `SomeTypedDict(...)` by default; annotated
  empty dictionaries such as `payload: SomeTypedDict = {}` are only for
  unavoidable incremental assembly.
- Avoid pushing `dict[str, Any]` through the core adapter surface.
- Avoid broad `dict[str, object]` in production source unless the dynamic boundary truly requires it.
- If a raw dictionary shape must remain, keep it localized to the parsing/normalization seam and add a short justification comment explaining why a stronger contract is not yet justified.
- Avoid broad `Any` unless the dynamic boundary truly requires it.
- If a runtime seam is inherently dynamic, localize that looseness to parsing/normalization boundaries and convert to explicit contracts quickly.

## Type Hygiene Rule

Strong typing should reduce code, not create defensive boilerplate.

Do not add broad `object` / `Any` annotations, casts, helper functions, or
justification comments only to satisfy Pyrefly or guardrails when an existing
framework contract already validates the value.

Preferred order when Pyrefly reports a type issue:

1. tighten the field, DTO, or helper signature;
2. rely on the existing Pydantic/domain contract when it already performs the
   validation;
3. introduce a narrow normalization helper only when the boundary really accepts
   more than the annotated contract;
4. add a broad type plus justification only for genuinely dynamic seams such as
   raw transport payloads, framework callback surfaces, settings coercion, or
   compatibility normalization.

Bad direction:

```python
# Broad type justified: Pydantic before validators receive raw boundary input.
def _item_type(value: object) -> ItemType:
    if isinstance(value, ItemType):
        return value
    if isinstance(value, str):
        return ItemType(value)
    raise ValueError("item_type must be a valid item type")
```

Preferred direction:

```python
item_type: ItemType
```

If a broad type remains, the justification must explain the real dynamic
boundary behavior, not merely restate that a type checker required it.

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
- do not reimplement Pydantic's built-in enum parsing just to make Pyrefly
  accept a before-validator signature.

## Boundary With Other Rule Sets

This file does not own return style, async placement, class size, or module
split thresholds. Those rules live in:

- `backend/.agents/rule/layout_rule/module-cohesion-rules.md`

Keep this file focused on type, enum, `TypedDict`, and explicit contract policy.

## Design Principle

This repository should prefer one explicit, strongly typed contract language and a predictable static type discipline.

The detailed contract language rules are defined in the Pydantic rule set.
The broader repository typing policy is defined here.
