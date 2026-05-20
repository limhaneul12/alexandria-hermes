"""Native Typer commands for MCP server operations."""

from __future__ import annotations

import typer
from app.cli_support.contracts.runtime_command_contracts import McpServeCommand
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


def handle_mcp_serve(command: McpServeCommand) -> int:
    """Run the MCP server from the CLI command contract.

    Args:
        command: CLI command contract containing the selected transport.

    Returns:
        Process-style exit code from the MCP server runner.
    """
    # lazy import justified: MCP server dependencies load only for the mcp serve command.
    from app.mcp_server.server_runtime import main as mcp_main

    exit_code = mcp_main(["--transport", command.transport.value])
    return exit_code
