# Changelog

All notable changes to Alexandria-Hermes are tracked here.

This project uses human-readable release notes grouped by date until versioned releases are introduced.

## Unreleased

### Added

- Added memory compact storage, routes, CLI/MCP tooling, migrations, and frontend
  pages for browsing current and historical compaction artifacts.
- Added librarian brief/domain entities, knowledge packet compilation, librarian
  chat UI/API routes, and provider delegate execution coverage.
- Added library search endpoints, service/domain query models, scale guard tests,
  and frontend prompt/skill creation/navigation flows.
- Added retrieval boundary routes/schemas for explicit retrieval policy edges.
- Added single-operator security coverage for localhost-first deployment and
  control-plane operator-key handling.
- Added a Hermes usage policy contract at `~/.hermes/alexandria-hermes/policy.yaml`.
- Added Hermes policy CLI commands:
  - `alexandria-hermes hermes policy status`
  - `alexandria-hermes hermes policy enable`
  - `alexandria-hermes hermes policy disable`
- Added default-on Alexandria usage semantics for Hermes onboarding.
- Added explicit self-acquisition fallback semantics: librarian collaboration is optional, and Hermes can still research and submit draft candidates directly when no librarian is configured.
- Added `policy_installed` to Hermes doctor output.
- Added a usage guidebook under `docs/usage_guidebook/` with feature-folder examples.
- Added regression coverage requiring installed Hermes assets to self-identify as local-first / Alexandria-when-needed, with `START_HERE` bootstrap guidance only when local context is insufficient for unfamiliar agents.

### Changed

- Hardened context and library repository search paths to avoid raw user SQL by
  using ORM/Core statements, bound parameters, and constrained FTS query
  normalization.
- Folded the separate memory-compacts implementation into the memory module and
  kept only documented compatibility aliases for public CLI/MCP names.
- Moved librarian/provider client contracts to domain-owned boundaries and made
  route exception mappings domain-specific.
- Removed unused package `__init__.py` files and added guardrails so app modules
  use explicit import surfaces instead of stale package re-exports.
- Updated README, install, Docker, and usage-guide docs for no-login,
  single-operator, localhost-first operation with `ALEXANDRIA_OPERATOR_API_KEY`.
- Removed stale README legacy references and expanded the Configuration section
  around the current backend, frontend proxy, CLI, Hermes, and MCP environment
  contracts.
- Updated `install.md` to document the policy contract, CLI on/off flow, guidebook links, and first-user expectations.
- Updated generated Hermes skill/prompt assets so they respect `policy.yaml` and describe librarian collaboration as optional.
- Updated generated Hermes skill/prompt assets to make Alexandria a durable library/long-term-memory layer that is used after current/local context proves insufficient, rather than a feature the user must manually invoke or a tool called before every task.
- Updated Hermes onboarding output so `policy.yaml` is part of installed/planned artifacts.

### Fixed

- Fixed app-layer enum/schema boundary rehydration after strict shared schema
  normalization so service/router logic receives typed enums where expected.
- Fixed package metadata naming so the backend installs as `alexandria-hermes`
  instead of stale `omx_remote` metadata.
- Fixed provider delegate error handling to catch explicit OpenAI SDK failures
  without swallowing unexpected local programming errors.

### Verified

- `make ci` → `ruff format --check`, `ruff check`, `pyrefly check`, guardrails
  `33 passed`, full backend pytest `324 passed`
- `npm run security:npm-supply-chain`
- `npm run lint`
- `npm run build`
- `git diff --check`

## 2026-05-16

### Added

- Initial changelog for Hermes policy/onboarding documentation work.
