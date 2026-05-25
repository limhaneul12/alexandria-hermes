"""Typed runtime setup result schemas."""

from __future__ import annotations

from app.shared.schemas.common_schemas import StrictSchemaModel


class HermesAssetsSetupSummary(StrictSchemaModel):
    """Planned or written Hermes awareness asset paths."""

    planned_files: list[str]
    written_files: list[str]


class MigrationSetupSummary(StrictSchemaModel):
    """Setup-triggered Alembic migration result."""

    run_requested: bool
    status: str
    revision: str | None


class SetupSummary(StrictSchemaModel):
    """CLI setup result payload."""

    mode: str
    dry_run: bool
    applied: bool
    hermes_home: str
    state_root: str
    env_path: str
    env_written: bool
    database_path: str
    database_url: str
    obsidian_vault_path: str
    alexandria_obsidian_root: str
    backend_log_path: str
    run_dir: str
    guidebook_path: str
    guidebook_written: bool
    hermes_assets_planned: bool
    hermes_assets: HermesAssetsSetupSummary
    migrations: MigrationSetupSummary
    next_steps: list[str]
