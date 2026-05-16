# Changelog

All notable changes to Alexandria-Hermes are tracked here.

This project uses human-readable release notes grouped by date until versioned releases are introduced.

## Unreleased

### Added

- Added a Hermes usage policy contract at `~/.hermes/alexandria-hermes/policy.yaml`.
- Added Hermes policy CLI commands:
  - `alexandria-hermes hermes policy status`
  - `alexandria-hermes hermes policy enable`
  - `alexandria-hermes hermes policy disable`
- Added default-on Alexandria usage semantics for Hermes onboarding.
- Added explicit self-acquisition fallback semantics: librarian collaboration is optional, and Hermes can still research and submit draft candidates directly when no librarian is configured.
- Added `policy_installed` to Hermes doctor output.
- Added a usage guidebook under `docs/usage_guidebook/` with feature-folder examples.
- Added regression coverage requiring installed Hermes assets to self-identify as a quiet default recall layer with `START_HERE` bootstrap guidance for unfamiliar agents.

### Changed

- Updated `install.md` to document the policy contract, CLI on/off flow, guidebook links, and first-user expectations.
- Updated generated Hermes skill/prompt assets so they respect `policy.yaml` and describe librarian collaboration as optional.
- Updated generated Hermes skill/prompt assets to make Alexandria an automatic awareness/default recall layer rather than a feature the user must manually invoke.
- Updated Hermes onboarding output so `policy.yaml` is part of installed/planned artifacts.

### Verified

- `uv run pytest tests/cli/test_hermes_cli.py -q -k 'hermes_onboard_dry_run_plans_prompts_skill_and_mcp_config or hermes_install_writes_default_enabled_policy_contract or hermes_policy_cli_toggles_usage_contract or hermes_install_apply_restart_hint_prints_first_prompt or hermes_doctor_deep_reports_readiness_checks or hermes_install_prompts_includes_self_acquisition_loop'`
- `uv run ruff check ...`
- `uv run pyrefly check ...`
- `make ci` → `279 passed`
- CLI smoke for `hermes policy status`, `disable`, and `enable`

## 2026-05-16

### Added

- Initial changelog for Hermes policy/onboarding documentation work.
