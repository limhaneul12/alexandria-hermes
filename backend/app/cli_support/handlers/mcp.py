"""Handlers for MCP server CLI commands."""

from __future__ import annotations

from app.cli_support.contracts.command_contracts import McpServeCommand


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
