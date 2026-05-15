"""Schemas for Hermes integration CLI output and config artifacts."""

from __future__ import annotations

from app.mcp_server.mcp_protocol_enums import (
    McpExecutable,
    McpLaunchArgument,
    McpServerKey,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from pydantic import Field


class McpServerEnvironment(StrictSchemaModel):
    """Environment variables written into the Hermes MCP config."""

    alexandria_api_url: str = Field(serialization_alias="ALEXANDRIA_API_URL")
    alexandria_api_token: str = Field(serialization_alias="ALEXANDRIA_API_TOKEN")
    hermes_home: str = Field(serialization_alias="HERMES_HOME")


class McpServerLaunch(StrictSchemaModel):
    """One MCP server launch contract for Hermes configuration."""

    command: McpExecutable
    args: tuple[McpLaunchArgument, McpLaunchArgument]
    env: McpServerEnvironment


class McpConfiguration(StrictSchemaModel):
    """Complete MCP configuration payload written for Hermes."""

    mcp_servers: dict[McpServerKey, McpServerLaunch] = Field(
        serialization_alias="mcpServers"
    )


class HermesBundleInstallationResult(StrictSchemaModel):
    """CLI result for installing or previewing Hermes integration files."""

    hermes_home: str
    source: str
    dry_run: bool
    planned_files: tuple[str, ...]
    written: tuple[str, ...]
    skipped: tuple[str, ...]
    backups: tuple[str, ...]
    mcp_config: McpConfiguration


class HermesConfigurationResult(StrictSchemaModel):
    """CLI result for writing Hermes local configuration."""

    hermes_home: str
    config_path: str
    dry_run: bool
    mcp_config: McpConfiguration


class HermesLocalConfiguration(StrictSchemaModel):
    """Local CLI configuration persisted for Hermes integration."""

    hermes_home: str
    api_url: str
    source: str


class HermesDoctorResult(StrictSchemaModel):
    """CLI diagnostic result for Hermes integration state."""

    hermes_home: str
    source: str
    exists: bool
    is_dir: bool
    writable: bool
    alexandria_dir: bool
    skill_installed: bool
    mcp_config_installed: bool
    config_path: str
    mcp_config: McpConfiguration


class HermesScannedFile(StrictSchemaModel):
    """One Alexandria-Hermes file discovered inside a Hermes directory."""

    path: str
    size_bytes: int


class HermesScanResult(StrictSchemaModel):
    """CLI result for scanning installed Hermes integration files."""

    path: str
    files: tuple[HermesScannedFile, ...]
