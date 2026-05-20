"""Typer commands for local setup and foreground backend runtime."""

from __future__ import annotations

import typer
from app.cli_support.contracts.runtime_command_contracts import (
    ServeCommand,
    SetupCommand,
)
from app.cli_support.handlers.runtime import handle_serve
from app.cli_support.presentation.output_renderers import print_json
from app.cli_support.setup.setup_service import handle_setup
from app.cli_support.typer_commands.command_choices import SetupRuntimeMode
from app.cli_support.typer_commands.typer_runtime import command_context
from app.shared.exceptions.cli_exceptions import CliInputError

setup_app = typer.Typer(
    add_completion=False,
    invoke_without_command=True,
    help=(
        "Configure supported Alexandria-Hermes runtimes: full-stack compose, "
        "full-stack separate processes, Backend + SQLite daemon, or guidebook-only. "
        "SQLite is the only supported database."
    ),
)


@setup_app.callback()
def setup(
    ctx: typer.Context,
    mode: SetupRuntimeMode | None = typer.Option(
        None,
        "--mode",
        help=(
            "Runtime mode: fullstack-compose, fullstack-separate, "
            "backend-daemon, or guidebook-only. Required for agent/non-interactive setup."
        ),
    ),
    hermes_home: str | None = typer.Option(
        None,
        "--hermes-home",
        envvar="HERMES_HOME",
        help="Hermes home directory; defaults to HERMES_HOME or ~/.hermes.",
    ),
    env_path: str | None = typer.Option(
        None,
        "--env-path",
        help="Override generated .env path.",
    ),
    api_url: str | None = typer.Option(
        None,
        "--api-url",
        help="Backend API URL to write into generated local env.",
    ),
    operator_api_key: str | None = typer.Option(
        None,
        "--operator-api-key",
        help="Operator API key to write; generated when omitted and --apply is used.",
    ),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Fail unless --mode is supplied; intended for agent-delegated installs.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview setup without writing files.",
    ),
    apply: bool = typer.Option(
        False,
        "--apply",
        help="Write local runtime files. Ignored when --dry-run is set.",
    ),
    write_guidebook: bool = typer.Option(
        False,
        "--write-guidebook",
        help="Write GUIDEBOOK.md for the selected runtime when applying.",
    ),
    install_hermes_assets: bool = typer.Option(
        False,
        "--install-hermes-assets",
        help="Plan or write Hermes awareness skill/prompt/policy assets.",
    ),
) -> None:
    """Configure a supported Alexandria-Hermes runtime.

    Args:
        ctx: Typer command context.
        mode: Selected runtime mode.
        hermes_home: Hermes home override.
        env_path: Generated env path override.
        api_url: Backend API URL for generated env.
        operator_api_key: Operator API key for generated env.
        non_interactive: Whether mode selection must be explicit.
        dry_run: Whether to avoid side effects.
        apply: Whether to write files.
        write_guidebook: Whether to write a guidebook.
        install_hermes_assets: Whether to plan/write Hermes awareness assets.

    Returns:
        None.
    """
    if ctx.invoked_subcommand is not None:
        return
    context = command_context(ctx)
    try:
        payload = handle_setup(
            SetupCommand(
                mode=mode,
                hermes_home=hermes_home,
                env_path=env_path,
                api_url=api_url,
                operator_api_key=operator_api_key,
                non_interactive=non_interactive,
                dry_run=dry_run,
                apply=apply,
                write_guidebook=write_guidebook,
                install_hermes_assets=install_hermes_assets,
            )
        )
    except (CliInputError, OSError) as exc:
        print(f"error: {exc}", file=context.stderr)
        raise typer.Exit(1) from exc
    if context.json_output:
        print_json(payload.model_dump(mode="json"), context.stdout)
    else:
        print(
            f"Alexandria setup: {payload.mode} "
            f"({'dry-run' if payload.dry_run else 'applied' if payload.applied else 'planned'})",
            file=context.stdout,
        )
    raise typer.Exit(0)


def serve_command(
    env_file: str | None = typer.Option(
        None,
        "--env-file",
        help="Load generated backend + SQLite local daemon environment file.",
    ),
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        help="Backend bind host for the local SQLite companion service.",
    ),
    port: int = typer.Option(
        8000,
        "--port",
        help="Backend bind port for the local SQLite companion service.",
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        help="Enable uvicorn reload for local development.",
    ),
) -> None:
    """Run the Alexandria-Hermes backend with the SQLite local DB in foreground.

    Args:
        env_file: Optional environment file to load before starting.
        host: Backend bind host.
        port: Backend bind port.
        reload: Whether to enable uvicorn reload for local development.
    """
    raise typer.Exit(
        handle_serve(
            ServeCommand(
                env_file=env_file,
                host=host,
                port=port,
                reload=reload,
            )
        )
    )
