"""Schemas for Codex MCP integration CLI output."""

from __future__ import annotations

from app.mcp_server.mcp_protocol_enums import (
    McpExecutable,
    McpLaunchArgument,
    McpServerKey,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from pydantic import Field


class CodexMcpServerEnvironment(StrictSchemaModel):
    """Environment variables written into Codex MCP config."""

    alexandria_api_url: str = Field(serialization_alias="ALEXANDRIA_API_URL")
    alexandria_operator_api_key: str = Field(
        serialization_alias="ALEXANDRIA_OPERATOR_API_KEY"
    )


class CodexMcpServerLaunch(StrictSchemaModel):
    """One Codex MCP server launch contract."""

    name: McpServerKey
    command: McpExecutable
    args: tuple[McpLaunchArgument, McpLaunchArgument]
    env: CodexMcpServerEnvironment


class CodexMcpInstallationResult(StrictSchemaModel):
    """CLI result for installing or previewing Codex MCP config."""

    codex_home: str
    config_path: str
    dry_run: bool
    written: tuple[str, ...]
    skipped: tuple[str, ...]
    backups: tuple[str, ...]
    mcp_server: CodexMcpServerLaunch
    restart_hint: str
