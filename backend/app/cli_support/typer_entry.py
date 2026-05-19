"""Native Typer command tree for the Alexandria-Hermes CLI."""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import redirect_stderr, redirect_stdout

import click
import typer
from app.cli_support.contracts.runtime_contracts import (
    DEFAULT_API_URL,
    DEFAULT_TIMEOUT_SECONDS,
    CliRuntime,
    CommandContext,
)
from app.cli_support.handlers.library import handle_health
from app.cli_support.typer_commands.collaboration import librarian_app, usage_app
from app.cli_support.typer_commands.context import context_app
from app.cli_support.typer_commands.daemon import daemon_app
from app.cli_support.typer_commands.hermes import hermes_app
from app.cli_support.typer_commands.library import (
    folders_app,
    library_app,
    minio_app,
    skills_app,
)
from app.cli_support.typer_commands.library_prompts import prompts_app
from app.cli_support.typer_commands.mcp import mcp_app
from app.cli_support.typer_commands.memory_compact import memory_compact_app
from app.cli_support.typer_commands.runtime import serve_command
from app.cli_support.typer_commands.setup import setup_app
from app.cli_support.typer_commands.typer_runtime import run_context
from app.cli_support.url_paths import normalized_base_url
from app.mcp_server.mcp_protocol_enums import McpLaunchArgument
from app.shared.exceptions.cli_exceptions import CliRuntimeStateError

CLI_PROG_NAME = "alexandria-hermes"

typer_app = typer.Typer(
    add_completion=False,
    help="Alexandria-Hermes command line client",
)
typer_app.add_typer(skills_app, name="skills")
typer_app.add_typer(prompts_app, name="prompts")
typer_app.add_typer(folders_app, name="folders")
typer_app.add_typer(library_app, name="library")
typer_app.add_typer(minio_app, name="minio")
typer_app.add_typer(context_app, name="context")
typer_app.add_typer(memory_compact_app, name="memory-compacts")
typer_app.add_typer(setup_app, name="setup")
typer_app.add_typer(daemon_app, name="daemon")
typer_app.add_typer(hermes_app, name="hermes")
typer_app.add_typer(librarian_app, name="librarian")
typer_app.add_typer(usage_app, name="usage")
typer_app.add_typer(mcp_app, name=McpLaunchArgument.MCP.value)
typer_app.command("serve")(serve_command)


@typer_app.callback()
def _configure(
    ctx: typer.Context,
    base_url: str = typer.Option(
        DEFAULT_API_URL,
        "--base-url",
        envvar="HERMES_API_URL",
        help="Backend API URL.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON output."),
    timeout: float = typer.Option(
        DEFAULT_TIMEOUT_SECONDS,
        "--timeout",
        help="HTTP timeout in seconds.",
    ),
    operator_api_key: str | None = typer.Option(
        None,
        "--operator-api-key",
        envvar="ALEXANDRIA_OPERATOR_API_KEY",
        help="Operator API key for sensitive settings/provider routes.",
    ),
) -> None:
    """Create the runtime context shared by command callbacks.

    Args:
        ctx: Typer context.
        base_url: Backend API URL.
        json_output: Whether JSON output was requested.
        timeout: HTTP timeout in seconds.
        operator_api_key: Operator API key header value.

    Returns:
        None.
    """
    runtime = ctx.obj
    if not isinstance(runtime, CliRuntime):
        raise CliRuntimeStateError("CLI runtime was not initialized")
    ctx.obj = CommandContext(
        base_url=normalized_base_url(base_url),
        json_output=json_output,
        operator_api_key=operator_api_key,
        timeout=max(1.0, float(timeout)),
        stdout=runtime.stdout,
        stderr=runtime.stderr,
        transport=runtime.transport,
    )


@typer_app.command("health")
def health(ctx: typer.Context) -> None:
    """Check backend health.

    Args:
        ctx: Typer context.

    Returns:
        None.
    """
    run_context(ctx, handle_health)


def invoke_typer_app(argv: Sequence[str], runtime: CliRuntime) -> int:
    """Run the native Typer command tree.

    Args:
        argv: Argument sequence excluding program name.
        runtime: Injected process resources.

    Returns:
        Process-style exit code.
    """
    command = typer.main.get_command(typer_app)
    with redirect_stdout(runtime.stdout), redirect_stderr(runtime.stderr):
        try:
            result = command.main(
                args=list(argv),
                prog_name=CLI_PROG_NAME,
                obj=runtime,
                standalone_mode=False,
            )
        except click.exceptions.ClickException as exc:
            exc.show(file=runtime.stderr)
            return int(exc.exit_code)
        except click.exceptions.Exit as exc:
            return int(exc.exit_code)
        except SystemExit as exc:
            if isinstance(exc.code, int):
                return exc.code
            return 1 if exc.code else 0
    if isinstance(result, int):
        return result
    return 0
