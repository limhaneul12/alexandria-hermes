"""Hermes integration CLI command contracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class HermesBundleCommand:
    """Shared parameters for Hermes bundle installation commands."""

    hermes_home: str | None
    api_url: str | None
    operator_api_key: str | None
    dry_run: bool
    overwrite: bool
    apply: bool
    restart_hint: bool
    print_first_prompt: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class HermesConfigureCommand:
    """Parameters for saving Hermes path configuration."""

    hermes_home: str | None
    api_url: str | None
    operator_api_key: str | None
    dry_run: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class HermesOnboardCommand(HermesBundleCommand):
    """Parameters for Hermes onboarding."""

    install_prompts: bool
    install_mcp: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class HermesInstallCommand(HermesBundleCommand):
    """Parameters for one-command Hermes installation."""


@dataclass(frozen=True, slots=True, kw_only=True)
class HermesDoctorCommand:
    """Parameters for Hermes diagnostics."""

    hermes_home: str | None
    api_url: str | None
    operator_api_key: str | None
    require_home: bool
    deep: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class HermesPolicyCommand:
    """Parameters for Hermes Alexandria usage policy commands."""

    hermes_home: str | None
    enabled: bool | None


@dataclass(frozen=True, slots=True, kw_only=True)
class HermesScanCommand:
    """Parameters for scanning Hermes Alexandria files."""

    path: str | None
    hermes_home: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class HermesSyncCommand(HermesBundleCommand):
    """Parameters for syncing Hermes prompt assets."""

    path: str | None
