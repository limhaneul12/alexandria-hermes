# Pydantic Rules Index

This directory is the source of truth for Pydantic-specific development rules in this repository.

Read these documents when changing schema design, validation policy, strictness, or boundary modeling.

## Documents

1. `00-overview.md`
   - Why this project uses Pydantic v2 as the primary contract system.
2. `01-configdict-and-model-shape.md`
   - How to use `ConfigDict`, `BaseModel`, and `RootModel`.
3. `02-strictness-defaults-and-nullability.md`
   - How to think about strict types, defaults, nullable fields, and omission.
4. `03-boundary-normalization.md`
   - How raw OMX payloads should be parsed, validated, and normalized.
5. `04-enums-literals-and-shared-types.md`
   - How to use enums, literals, and shared typed definitions.
