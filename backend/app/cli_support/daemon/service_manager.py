"""Local daemon service manager boundary."""

from __future__ import annotations

import platform
from pathlib import Path

from app.cli_support.daemon.launchd_service import render_launchd_plist
from app.cli_support.daemon.service_contracts import DaemonResult, ServiceDefinition
from app.cli_support.daemon.systemd_service import render_systemd_unit
from app.cli_support.setup.local_state import resolve_local_state

SERVICE_NAME = "alexandria-hermes-backend"
CLI_COMMAND = "alexandria-hermes"


def service_definition(
    *,
    hermes_home: str | None,
    env_file: str | None,
    host: str,
    port: int,
) -> ServiceDefinition:
    """Build the backend service definition for local daemon commands.

    Args:
        hermes_home: Optional Hermes home directory override.
        env_file: Optional environment file override.
        host: Backend service bind host.
        port: Backend service bind port.

    Returns:
        Service definition used by daemon lifecycle commands.
    """
    state = resolve_local_state(hermes_home)
    selected_env = Path(env_file).expanduser().resolve() if env_file else state.env_path
    return ServiceDefinition(
        service_name=SERVICE_NAME,
        env_file=selected_env,
        host=host,
        port=port,
        log_path=state.backend_log_path,
        cli_command=CLI_COMMAND,
    )


def handle_daemon_action(
    *,
    action: str,
    hermes_home: str | None,
    service_home: str | None,
    env_file: str | None,
    host: str,
    port: int,
    dry_run: bool,
    apply: bool,
) -> DaemonResult:
    """Handle local daemon lifecycle actions through a narrow boundary.

    Args:
        action: Daemon action name.
        hermes_home: Optional Hermes home directory override.
        service_home: Optional service manager home override.
        env_file: Optional environment file override.
        host: Backend service bind host.
        port: Backend service bind port.
        dry_run: Whether to render planned actions without applying writes.
        apply: Whether to apply supported install/uninstall actions.

    Returns:
        Daemon action result for CLI rendering.
    """
    service = service_definition(
        hermes_home=hermes_home,
        env_file=env_file,
        host=host,
        port=port,
    )
    service_file_path = _service_file_path(service_home)
    supported = service_file_path is not None
    warnings = (
        []
        if supported
        else ["Unsupported platform; use `alexandria-hermes serve` manually."]
    )
    commands = _commands(action, service, service_file_path)
    applied = False
    status = "planned"
    if action == "logs":
        status = "guidance"
    elif action == "status":
        status = _status(service_file_path)
    elif action == "install" and supported:
        if apply and not dry_run:
            _write_service_file(service_file_path, service)
            applied = True
            status = "installed"
        else:
            status = "dry-run" if dry_run else "planned"
    elif action == "uninstall" and service_file_path is not None:
        if apply and not dry_run and service_file_path.exists():
            service_file_path.unlink()
            applied = True
            status = "uninstalled"
        else:
            status = "dry-run" if dry_run else "planned"
    elif action in {"start", "stop"}:
        status = "command-guidance" if supported else "unsupported"
    elif not supported:
        status = "unsupported"
    return DaemonResult(
        action=action,
        supported=supported,
        service_name=SERVICE_NAME,
        service_file_path=str(service_file_path) if service_file_path else None,
        dry_run=dry_run,
        applied=applied,
        status=status,
        commands=commands,
        warnings=warnings,
        log_path=str(service.log_path) if action == "logs" else None,
    )


def _service_file_path(service_home: str | None) -> Path | None:
    home = Path(service_home).expanduser().resolve() if service_home else Path.home()
    system = platform.system()
    if system == "Darwin":
        return home / "Library" / "LaunchAgents" / "com.alexandria-hermes.backend.plist"
    if system == "Linux":
        return (
            home / ".config" / "systemd" / "user" / "alexandria-hermes-backend.service"
        )
    return None


def _write_service_file(path: Path, service: ServiceDefinition) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = (
        render_launchd_plist(service)
        if path.suffix == ".plist"
        else render_systemd_unit(service)
    )
    path.write_text(rendered, encoding="utf-8")


def _commands(
    action: str,
    service: ServiceDefinition,
    service_file_path: Path | None,
) -> list[str]:
    serve_command = (
        f"{service.cli_command} serve --env-file {service.env_file} "
        f"--host {service.host} --port {service.port}"
    )
    if action == "logs":
        return [f"tail -f {service.log_path}"]
    if service_file_path is None:
        return [serve_command]
    if service_file_path.suffix == ".plist":
        return _launchd_commands(action, service_file_path, serve_command)
    return _systemd_commands(action, service_file_path, serve_command)


def _launchd_commands(action: str, path: Path, serve_command: str) -> list[str]:
    if action == "install":
        return [serve_command, f"launchctl load {path}"]
    if action == "start":
        return ["launchctl kickstart gui/$(id -u)/com.alexandria-hermes.backend"]
    if action == "stop":
        return ["launchctl bootout gui/$(id -u)/com.alexandria-hermes.backend"]
    if action == "uninstall":
        return [f"launchctl unload {path}"]
    return ["launchctl print gui/$(id -u)/com.alexandria-hermes.backend"]


def _systemd_commands(action: str, path: Path, serve_command: str) -> list[str]:
    if action == "install":
        return [
            serve_command,
            "systemctl --user daemon-reload",
            "systemctl --user enable alexandria-hermes-backend",
        ]
    if action == "start":
        return ["systemctl --user start alexandria-hermes-backend"]
    if action == "stop":
        return ["systemctl --user stop alexandria-hermes-backend"]
    if action == "uninstall":
        return [f"rm {path}", "systemctl --user daemon-reload"]
    return ["systemctl --user status alexandria-hermes-backend"]


def _status(path: Path | None) -> str:
    if path is None:
        return "unsupported"
    if not path.exists():
        return "not-installed"
    return "unknown"
