# Pydantic Rules Index

This directory is the source of truth for Pydantic-specific development rules in this repository.

Read these documents when changing schema design, validation policy, strictness, or boundary modeling.

## Documents

1. `01-configdict-and-model-shape.md`
   - How to use `ConfigDict`, `BaseModel`, and `RootModel`.
2. `02-strictness-defaults-and-nullability.md`
   - How to think about strict types, defaults, nullable fields, and omission.
3. `03-boundary-normalization.md`
   - How raw boundary payloads should be parsed, validated, and normalized.
4. `schema-boundary-rules.md`
   - Where schema boundaries exist and how they are managed.

Related enum/literal/shared type policy lives at:

- `backend/.agents/rule/type_enum_rule/pydantic/04-enums-literals-and-shared-types.md`
