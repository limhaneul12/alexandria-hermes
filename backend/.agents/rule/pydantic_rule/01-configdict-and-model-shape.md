# ConfigDict and Model Shape Rules

## ConfigDict Rule

Use `model_config = ConfigDict(...)` explicitly when a schema needs configuration that differs from the shared strict default.

Do not copy the same `ConfigDict` block into every schema by habit.

If a named-field schema only needs the project strict default, prefer inheriting from the shared strict base in `schemas/common_schemas.py` instead of repeating the same per-class config block.

Keep a per-schema `ConfigDict(...)` only when that schema genuinely needs additional or different options.

### Shared strict base

For normal named-field schema contracts, the project strict base should be:

```python
ConfigDict(
    extra="forbid",
    frozen=True,
    use_enum_values=True,
    validate_default=True,
)
```

Meaning:

- `extra="forbid"` keeps stable adapter contracts closed by default.
- `frozen=True` makes schema instances immutable contract values.
- `use_enum_values=True` preserves string-centered JSON/CLI/artifact boundaries.
- `validate_default=True` ensures unavoidable defaults are still validated.

`validate_default=True` is not permission to add convenience defaults. Defaults still require a real contract reason.

Because `use_enum_values=True` can normalize enum-backed fields to their string values at runtime, do not compare enum-backed schema fields with `is` or `is not`. Use equality against the enum member or its `.value`.

### Shared root-schema base

For root-value schema contracts, use a separate root base such as `StrictRootSchemaModel`.

The root base should not include `extra="forbid"`, because `RootModel` has no named extra fields to forbid. The root base should instead use:

```python
ConfigDict(
    frozen=True,
    use_enum_values=True,
    validate_default=True,
)
```

Do not make ordinary schemas inherit from the root base, and do not make root schemas inherit from the named-field strict base.

### Preferred direction

- Choose `ConfigDict` options intentionally.
- Add only the options that match the contract.
- Use the shared named-field strict base for ordinary stable contracts.
- Use the shared root strict base for root-value contracts.
- Avoid template-style config copy-paste.

### Options not enabled globally

Do not add these to the shared base by default:

- `strict=True`
- `validate_assignment=True`
- `str_strip_whitespace=True`
- `str_min_length=1`
- `populate_by_name=True`
- `arbitrary_types_allowed=True`
- `from_attributes=True`

Use them only on a schema that has a specific contract reason.

### Project stance

`ConfigDict` should be optimized for each schema’s actual job.
The shared base exists to encode this repository’s common stable contract, not to become an unreviewed dumping ground for every Pydantic option.

## BaseModel Rule

Use `BaseModel` for normal named-field contracts.

This is the default shape for most schemas in this repository.

Examples:
- runtime status
- execution event
- team status
- search request
- normalized payload response

## RootModel Rule

`RootModel` is allowed, but only when the payload truly is a root value contract.

Examples of acceptable `RootModel` usage:
- the entire payload is a list/array with domain meaning;
- the entire payload is a dictionary with domain meaning;
- the entire payload is a single root value with no meaningful named wrapper fields.

### Root schema collection rule

Use a root schema when a collection itself carries domain meaning, validation, or helper behavior.

Good candidates:
- `MultiOperatorSnapshot` flow collections;
- active/launchable/resumable/cleanup/terminal flow ID buckets;
- worker assignment collections where duplicate workers or duplicate owned files must be rejected;
- repeated `NonEmptyString` token collections that represent a named contract rather than incidental local data.

Do not use raw `list[...]` at stable schema boundaries just because JSON represents the value as an array. Prefer:

- `tuple[T, ...]` for an immutable ordered sequence representation when duplicates are allowed and no collection-level domain validation is needed;
- `StrictRootSchemaModel[tuple[T, ...]]` when the collection itself owns invariants or helper methods.

Remember: `tuple[T, ...]` preserves ordering and immutability, but it does not reject duplicates. If duplicate rejection, membership checks, bucket consistency, or named helpers matter, model the collection as a root schema and validate there.

### Project stance

- `RootModel` is not the default.
- Use `BaseModel` for ordinary named-field contracts.
- Use `RootModel` only when the payload shape clearly demands it.
- Use `StrictRootSchemaModel` for root-value contracts that should share this repo’s immutable enum/string boundary behavior.

If the answer to “is the root itself the contract?” is not clearly yes, use `BaseModel`.

## Model API Rule

Prefer Pydantic v2 APIs consistently.

Preferred methods:
- `model_validate(...)`
- `model_validate_json(...)`
- `model_dump(...)`
- `model_dump_json(...)`

Avoid carrying older v1-style parsing and dumping habits into this repository.
