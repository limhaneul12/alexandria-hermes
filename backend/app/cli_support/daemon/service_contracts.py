"""Typed contracts for local daemon service definitions and results."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.shared.schemas.common_schemas import StrictSchemaModel


@dataclass(frozen=True, slots=True, kw_only=True)
class ServiceDefinition:
    """Runtime data needed to render a local backend service file."""

    service_name: str
    env_file: Path
    host: str
    port: int
    log_path: Path
    cli_command: str


class DaemonResult(StrictSchemaModel):
    """CLI result for daemon lifecycle commands."""

    action: str
    supported: bool
    service_name: str
    service_file_path: str | None
    dry_run: bool
    applied: bool
    status: str
    commands: list[str]
    warnings: list[str]
    log_path: str | None = None
