"""Native Typer commands for Codex integration operations."""

from __future__ import annotations

import typer
from app.cli_support.contracts.codex_command_contracts import CodexMcpInstallCommand
from app.cli_support.contracts.runtime_contracts import CommandContext
from app.cli_support.presentation.output_renderers import print_codex_payload
from app.cli_support.support.codex.mcp_config import install_codex_mcp_config
from app.cli_support.typer_commands.typer_runtime import run_local

codex_app = typer.Typer(help="Install Alexandria-Hermes assets into Codex")


@codex_app.command("install-mcp")
def codex_install_mcp(
    ctx: typer.Context,
    codex_home: str | None = typer.Option(
        None,
        "--codex-home",
        envvar="CODEX_HOME",
    ),
    api_url: str | None = typer.Option(
        None,
        "--api-url",
        envvar="ALEXANDRIA_API_URL",
    ),
    operator_api_key: str | None = typer.Option(
        None,
        "--operator-api-key",
        envvar="ALEXANDRIA_OPERATOR_API_KEY",
    ),
    overwrite: bool = typer.Option(False, "--overwrite"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Install Alexandria MCP config into Codex config.toml.

    Args:
        ctx: Typer context.
        codex_home: Optional Codex home path.
        api_url: Optional Alexandria API URL.
        operator_api_key: Optional Alexandria operator API key.
        overwrite: Whether to replace an unmanaged Alexandria MCP server block.
        dry_run: Whether to preview changes only.

    Returns:
        None.
    """
    run_local(
        ctx,
        CodexMcpInstallCommand(
            codex_home=codex_home,
            api_url=api_url,
            operator_api_key=operator_api_key,
            dry_run=dry_run,
            overwrite=overwrite,
        ),
        handle_codex_install_mcp,
    )


def handle_codex_install_mcp(
    command: CodexMcpInstallCommand,
    context: CommandContext,
) -> int:
    """Install Codex MCP integration config.

    Args:
        command: CLI command contract with install options.
        context: Runtime context containing output streams and default API URL.

    Returns:
        Process-style exit code.
    """
    payload = install_codex_mcp_config(command=command, context=context)
    print_codex_payload(payload, context)
    return 0
