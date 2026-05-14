# Strictness, Defaults, and Nullability Rules

## Constrained Primitive Rule

When a field carries a reusable constrained primitive contract, prefer an explicit constrained alias over repeating ad-hoc `Field(...)` rules on plain primitives.

Good candidates:
- non-empty strings
- bounded identifiers
- normalized tokens that carry the same validation rule in more than one schema

Preferred direction:
- use `Annotated[...]` with Pydantic v2 constraint helpers when the constraint is part of the type meaning,
- keep one-off field metadata inline only when the rule is truly local to a single field,
- avoid scattering repeated `Field(min_length=1)` style fragments across multiple schemas when they represent the same concept.

This helps preserve contract meaning at the type layer instead of hiding it inside repeated field declarations.

## Strictness Rule

Strictness should be used intentionally, not automatically.

### Project stance

- `StrictStr`, `StrictInt`, `StrictBool`, and model-level `strict=True` are **not** default choices.
- Do not apply strict types everywhere just to appear rigorous.
- Use strictness only when coercion would violate the real contract.

### Good strictness candidates

- protocol discriminators
- runtime modes
- event kinds
- boolean flags where coercion is risky
- machine-controlled contracts where silent coercion would hide a bug

### Review question

Before using strict types, ask:
- Does coercion here create real contract risk?

If the answer is no, strictness may be unnecessary.

## Defaults Rule

Do not use default values casually.

### Project stance

- Defaults should be introduced only when they are truly unavoidable or when the contract explicitly requires a real default.
- Required fields should stay required unless there is a concrete contract reason to relax them.
- Do not let defaults become a convenience escape hatch for incomplete schema design.
- `validate_default=True` on the shared schema base exists to validate unavoidable defaults, not to encourage new defaults.

If a default exists, it should be explainable as part of the contract, not merely as a coding convenience.

### Collection default caution

Avoid `default_factory=list` on stable schema-boundary collections unless an empty collection is genuinely the protocol default.

If a collection has domain meaning, prefer an explicit required field plus a root schema that validates the collection contract. Empty collections should be passed deliberately by the caller when they are meaningful.

## Nullability Rule

Do not use `| None` by default.

### Project stance

- Nullable fields should exist only when absence is a real part of the contract.
- Do not use nullable fields as a shortcut for incomplete thinking.
- Omission, nullability, and defaulting are different decisions and should not be blurred together.

## Fallback Rule

Do not hide missing data with broad fallback expressions inside schema construction.

Avoid patterns such as:
- `or {}`
- `or []`
- `or ""`

If a fallback is truly part of the contract, normalize it intentionally before or during schema construction and keep the rule explicit.
