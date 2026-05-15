"""MCP protocol-local enum contracts."""

from __future__ import annotations

from enum import StrEnum


class McpTransport(StrEnum):
    """MCP server transport modes accepted by the CLI entrypoint."""

    STDIO = "stdio"
    SSE = "sse"
    STREAMABLE_HTTP = "streamable-http"


class McpServerKey(StrEnum):
    """Hermes MCP configuration server keys owned by this integration."""

    ALEXANDRIA = "alexandria"


class McpExecutable(StrEnum):
    """Executable names emitted into Hermes MCP configuration."""

    ALEXANDRIA_HERMES = "alexandria-hermes"


class McpLaunchArgument(StrEnum):
    """Command arguments emitted into Hermes MCP configuration."""

    MCP = "mcp"
    SERVE = "serve"


class McpContextTag(StrEnum):
    """Context tags emitted by MCP capture tools."""

    MCP = "mcp"
    CAPTURE = "capture"
    HERMES = "hermes"
    CANDIDATE = "candidate"
