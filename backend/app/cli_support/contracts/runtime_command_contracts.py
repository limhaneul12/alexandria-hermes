"""Runtime CLI command contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.mcp_server.mcp_protocol_enums import McpTransport


class SetupRuntimeMode(StrEnum):
    """Supported Alexandria-Hermes runtime setup modes."""

    BACKEND_DAEMON = "backend-daemon"
    GUIDEBOOK_ONLY = "guidebook-only"


@dataclass(frozen=True, slots=True, kw_only=True)
class NoArgsCommand:
    """Parameters for commands without command-specific inputs."""


@dataclass(frozen=True, slots=True, kw_only=True)
class ServeCommand:
    """Parameters for running the backend foreground server."""

    env_file: str | None
    host: str
    port: int
    reload: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class DaemonCommand:
    """Parameters for local backend daemon lifecycle commands."""

    action: str
    hermes_home: str | None
    service_home: str | None
    env_file: str | None
    host: str
    port: int
    dry_run: bool
    apply: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class SetupCommand:
    """Parameters for Alexandria-Hermes runtime setup."""

    mode: SetupRuntimeMode | None
    hermes_home: str | None
    env_path: str | None
    api_url: str | None
    obsidian_vault_path: str | None
    alexandria_obsidian_root: str | None
    operator_api_key: str | None
    non_interactive: bool
    dry_run: bool
    apply: bool
    write_guidebook: bool
    install_hermes_assets: bool
    run_migrations: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class McpServeCommand:
    """Parameters for running the MCP server."""

    transport: McpTransport
