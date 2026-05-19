"""Daemon command handlers."""

from __future__ import annotations

from app.cli_support.contracts.command_contracts import DaemonCommand
from app.cli_support.daemon.service_contracts import DaemonResult
from app.cli_support.daemon.service_manager import handle_daemon_action


def handle_daemon(command: DaemonCommand) -> DaemonResult:
    """Handle a local backend daemon lifecycle command.

    Args:
        command: Daemon command options.

    Returns:
        Daemon action result for CLI rendering.
    """
    return handle_daemon_action(
        action=command.action,
        hermes_home=command.hermes_home,
        service_home=command.service_home,
        env_file=command.env_file,
        host=command.host,
        port=command.port,
        dry_run=command.dry_run,
        apply=command.apply,
    )
