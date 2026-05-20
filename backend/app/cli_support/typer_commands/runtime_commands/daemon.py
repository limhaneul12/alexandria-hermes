"""Typer commands for the local backend daemon lifecycle."""

from __future__ import annotations

import typer
from app.cli_support.contracts.runtime_command_contracts import DaemonCommand
from app.cli_support.daemon.service_manager import handle_daemon_action
from app.cli_support.presentation.output_renderers import print_json
from app.cli_support.typer_commands.typer_runtime import command_context
from app.shared.exceptions.cli_exceptions import CliInputError

daemon_app = typer.Typer(
    add_completion=False,
    help="Install/start/stop/status/logs for the backend + SQLite local daemon.",
)


def _run_daemon(
    ctx: typer.Context,
    *,
    action: str,
    hermes_home: str | None,
    service_home: str | None,
    env_file: str | None,
    host: str,
    port: int,
    dry_run: bool,
    apply: bool,
) -> None:
    context = command_context(ctx)
    try:
        command = DaemonCommand(
            action=action,
            hermes_home=hermes_home,
            service_home=service_home,
            env_file=env_file,
            host=host,
            port=port,
            dry_run=dry_run,
            apply=apply,
        )
        payload = handle_daemon_action(
            action=command.action,
            hermes_home=command.hermes_home,
            service_home=command.service_home,
            env_file=command.env_file,
            host=command.host,
            port=command.port,
            dry_run=command.dry_run,
            apply=command.apply,
        )
    except (CliInputError, OSError) as exc:
        print(f"error: {exc}", file=context.stderr)
        raise typer.Exit(1) from exc
    if context.json_output:
        print_json(payload.model_dump(mode="json"), context.stdout)
    else:
        print(
            f"daemon {payload.action}: {payload.status} ({payload.service_name})",
            file=context.stdout,
        )
    raise typer.Exit(0)


def _shared_hermes_home() -> str | None:
    return typer.Option(
        None,
        "--hermes-home",
        envvar="HERMES_HOME",
        help="Hermes home directory; defaults to HERMES_HOME or ~/.hermes.",
    )


def _shared_service_home() -> str | None:
    return typer.Option(
        None,
        "--service-home",
        help="Override service manager home for tests or custom local install paths.",
    )


def _shared_env_file() -> str | None:
    return typer.Option(
        None,
        "--env-file",
        help="Env file for alexandria-hermes serve; defaults to local setup .env.",
    )


@daemon_app.command("install")
def install(
    ctx: typer.Context,
    hermes_home: str | None = _shared_hermes_home(),
    service_home: str | None = _shared_service_home(),
    env_file: str | None = _shared_env_file(),
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    apply: bool = typer.Option(False, "--apply"),
) -> None:
    """Install the local backend daemon service file.

    Args:
        ctx: Typer command context.
        hermes_home: Optional Hermes home directory override.
        service_home: Optional service manager home override.
        env_file: Optional environment file override.
        host: Backend service bind host.
        port: Backend service bind port.
        dry_run: Whether to render planned actions without applying writes.
        apply: Whether to write the service file.
    """
    _run_daemon(
        ctx,
        action="install",
        hermes_home=hermes_home,
        service_home=service_home,
        env_file=env_file,
        host=host,
        port=port,
        dry_run=dry_run,
        apply=apply,
    )


@daemon_app.command("status")
def status(
    ctx: typer.Context,
    hermes_home: str | None = _shared_hermes_home(),
    service_home: str | None = _shared_service_home(),
    env_file: str | None = _shared_env_file(),
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
) -> None:
    """Report local backend daemon installation status.

    Args:
        ctx: Typer command context.
        hermes_home: Optional Hermes home directory override.
        service_home: Optional service manager home override.
        env_file: Optional environment file override.
        host: Backend service bind host.
        port: Backend service bind port.
    """
    _run_daemon(
        ctx,
        action="status",
        hermes_home=hermes_home,
        service_home=service_home,
        env_file=env_file,
        host=host,
        port=port,
        dry_run=False,
        apply=False,
    )


@daemon_app.command("logs")
def logs(
    ctx: typer.Context,
    hermes_home: str | None = _shared_hermes_home(),
    service_home: str | None = _shared_service_home(),
    env_file: str | None = _shared_env_file(),
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
) -> None:
    """Print log path and tail guidance for the local backend daemon.

    Args:
        ctx: Typer command context.
        hermes_home: Optional Hermes home directory override.
        service_home: Optional service manager home override.
        env_file: Optional environment file override.
        host: Backend service bind host.
        port: Backend service bind port.
    """
    _run_daemon(
        ctx,
        action="logs",
        hermes_home=hermes_home,
        service_home=service_home,
        env_file=env_file,
        host=host,
        port=port,
        dry_run=False,
        apply=False,
    )


@daemon_app.command("start")
def start(
    ctx: typer.Context,
    hermes_home: str | None = _shared_hermes_home(),
    service_home: str | None = _shared_service_home(),
    env_file: str | None = _shared_env_file(),
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
) -> None:
    """Print start command guidance for the local backend daemon.

    Args:
        ctx: Typer command context.
        hermes_home: Optional Hermes home directory override.
        service_home: Optional service manager home override.
        env_file: Optional environment file override.
        host: Backend service bind host.
        port: Backend service bind port.
    """
    _run_daemon(
        ctx,
        action="start",
        hermes_home=hermes_home,
        service_home=service_home,
        env_file=env_file,
        host=host,
        port=port,
        dry_run=False,
        apply=False,
    )


@daemon_app.command("stop")
def stop(
    ctx: typer.Context,
    hermes_home: str | None = _shared_hermes_home(),
    service_home: str | None = _shared_service_home(),
    env_file: str | None = _shared_env_file(),
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
) -> None:
    """Print stop command guidance for the local backend daemon.

    Args:
        ctx: Typer command context.
        hermes_home: Optional Hermes home directory override.
        service_home: Optional service manager home override.
        env_file: Optional environment file override.
        host: Backend service bind host.
        port: Backend service bind port.
    """
    _run_daemon(
        ctx,
        action="stop",
        hermes_home=hermes_home,
        service_home=service_home,
        env_file=env_file,
        host=host,
        port=port,
        dry_run=False,
        apply=False,
    )


@daemon_app.command("uninstall")
def uninstall(
    ctx: typer.Context,
    hermes_home: str | None = _shared_hermes_home(),
    service_home: str | None = _shared_service_home(),
    env_file: str | None = _shared_env_file(),
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    apply: bool = typer.Option(False, "--apply"),
) -> None:
    """Uninstall the local backend daemon service file.

    Args:
        ctx: Typer command context.
        hermes_home: Optional Hermes home directory override.
        service_home: Optional service manager home override.
        env_file: Optional environment file override.
        host: Backend service bind host.
        port: Backend service bind port.
        dry_run: Whether to render planned actions without applying writes.
        apply: Whether to remove the service file.
    """
    _run_daemon(
        ctx,
        action="uninstall",
        hermes_home=hermes_home,
        service_home=service_home,
        env_file=env_file,
        host=host,
        port=port,
        dry_run=dry_run,
        apply=apply,
    )
