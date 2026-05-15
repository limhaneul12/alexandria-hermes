"""Native Typer commands for MCP server operations."""

from __future__ import annotations

import typer
from app.cli_support.contracts.command_contracts import McpServeCommand
from app.cli_support.handlers.mcp import handle_mcp_serve
from app.cli_support.typer_commands.typer_runtime import run_standalone
from app.mcp_server.mcp_protocol_enums import McpLaunchArgument, McpTransport

mcp_app = typer.Typer(help="Run MCP server")


@mcp_app.command(McpLaunchArgument.SERVE.value)
def mcp_serve(
    ctx: typer.Context,
    transport: McpTransport = typer.Option(McpTransport.STDIO, "--transport"),
) -> None:
    """Serve Alexandria-Hermes MCP.

    Args:
        ctx: Typer context.
        transport: MCP transport name.

    Returns:
        None.
    """
    run_standalone(McpServeCommand(transport=transport), handle_mcp_serve)
