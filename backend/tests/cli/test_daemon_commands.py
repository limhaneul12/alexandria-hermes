"""Behavior tests for local daemon lifecycle commands."""

from __future__ import annotations

import io
import json
from pathlib import Path

from app.cli import run


def _json_cli(argv: list[str]) -> tuple[int, dict[str, object], str]:
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = run(["--json", *argv], stdout=stdout, stderr=stderr)

    payload = json.loads(stdout.getvalue()) if stdout.getvalue().strip() else {}
    return exit_code, payload, stderr.getvalue()


def test_daemon_install_dry_run_reports_service_path_and_command(
    tmp_path: Path,
) -> None:
    """Daemon install dry-run plans local service without writing service files."""
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()

    exit_code, payload, stderr = _json_cli(
        [
            "daemon",
            "install",
            "--hermes-home",
            str(hermes_home),
            "--dry-run",
        ]
    )

    commands = "\n".join(str(command) for command in payload["commands"])
    assert exit_code == 0, stderr
    assert payload["action"] == "install"
    assert payload["dry_run"] is True
    assert payload["applied"] is False
    assert payload["service_file_path"]
    assert "alexandria-hermes serve" in commands
    assert not Path(str(payload["service_file_path"])).exists()


def test_daemon_status_json_is_typed_even_when_not_installed(tmp_path: Path) -> None:
    """Daemon status reports a stable not-installed payload."""
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()

    exit_code, payload, stderr = _json_cli(
        ["daemon", "status", "--hermes-home", str(hermes_home)]
    )

    assert exit_code == 0, stderr
    assert payload["action"] == "status"
    assert payload["service_name"] == "alexandria-hermes-backend"
    assert payload["status"] in {"not-installed", "unsupported", "unknown"}
    assert isinstance(payload["supported"], bool)
    assert isinstance(payload["warnings"], list)


def test_daemon_install_apply_writes_service_file_under_temp_home(
    tmp_path: Path,
) -> None:
    """Daemon install apply writes a local service definition only."""
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()

    exit_code, payload, stderr = _json_cli(
        [
            "daemon",
            "install",
            "--hermes-home",
            str(hermes_home),
            "--service-home",
            str(tmp_path),
            "--apply",
        ]
    )

    service_file_path = Path(str(payload["service_file_path"]))
    assert exit_code == 0, stderr
    assert payload["applied"] is True
    assert service_file_path.exists()
    assert "alexandria-hermes serve" in service_file_path.read_text(encoding="utf-8")


def test_daemon_logs_returns_log_path_and_tail_guidance(tmp_path: Path) -> None:
    """Daemon logs is safe guidance when direct tailing is not requested."""
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()

    exit_code, payload, stderr = _json_cli(
        ["daemon", "logs", "--hermes-home", str(hermes_home)]
    )

    commands = "\n".join(str(command) for command in payload["commands"])
    assert exit_code == 0, stderr
    assert payload["action"] == "logs"
    assert payload["log_path"] == str(
        hermes_home / "alexandria-hermes" / "logs" / "backend.log"
    )
    assert "tail -f" in commands
