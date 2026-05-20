"""Behavior tests for daemon service file renderers."""

from __future__ import annotations

from pathlib import Path

from app.cli_support.daemon.service_contracts import ServiceDefinition
from app.cli_support.daemon.service_manager import (
    render_launchd_plist,
    render_systemd_unit,
)


def _definition(tmp_path: Path) -> ServiceDefinition:
    hermes_home = tmp_path / "hermes"
    return ServiceDefinition(
        service_name="alexandria-hermes-backend",
        env_file=hermes_home / "alexandria-hermes" / ".env",
        host="127.0.0.1",
        port=8000,
        log_path=hermes_home / "alexandria-hermes" / "logs" / "backend.log",
        cli_command="alexandria-hermes",
    )


def test_launchd_plist_references_env_file_without_embedding_secrets(
    tmp_path: Path,
) -> None:
    """launchd renderer uses env-file reference and serve command, not raw secrets."""
    service = _definition(tmp_path)

    plist = render_launchd_plist(service)

    assert "alexandria-hermes" in plist
    assert "serve" in plist
    assert str(service.env_file) in plist
    assert "127.0.0.1" in plist
    assert "8000" in plist
    assert str(service.log_path) in plist
    assert "ALEXANDRIA_OPERATOR_API_KEY" not in plist


def test_systemd_unit_references_env_file_without_embedding_secrets(
    tmp_path: Path,
) -> None:
    """systemd renderer uses env-file reference and serve command, not raw secrets."""
    service = _definition(tmp_path)

    unit = render_systemd_unit(service)

    assert "ExecStart=alexandria-hermes serve" in unit
    assert str(service.env_file) in unit
    assert "127.0.0.1" in unit
    assert "8000" in unit
    assert str(service.log_path) in unit
    assert "ALEXANDRIA_OPERATOR_API_KEY" not in unit
