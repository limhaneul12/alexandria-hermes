"""Behavior tests for Alexandria runtime setup modes."""

from __future__ import annotations

import io
import json
from pathlib import Path

from app.cli import run


def _json_stdout(argv: list[str]) -> tuple[int, dict[str, object], str]:
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = run(["--json", *argv], stdout=stdout, stderr=stderr)

    payload = json.loads(stdout.getvalue()) if stdout.getvalue().strip() else {}
    return exit_code, payload, stderr.getvalue()


def test_setup_non_interactive_requires_runtime_mode() -> None:
    """Agent-delegated setup fails fast when runtime mode was not chosen."""
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = run(["setup", "--non-interactive"], stdout=stdout, stderr=stderr)

    assert exit_code != 0
    assert "--mode" in stderr.getvalue()
    assert stdout.getvalue() == ""


def test_setup_backend_daemon_dry_run_reports_sqlite_local_state(
    tmp_path: Path,
) -> None:
    """Backend-daemon setup previews Hermes-style SQLite local state."""
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()

    exit_code, payload, stderr = _json_stdout(
        [
            "setup",
            "--mode",
            "backend-daemon",
            "--hermes-home",
            str(hermes_home),
            "--dry-run",
        ]
    )

    assert exit_code == 0, stderr
    assert payload["mode"] == "backend-daemon"
    assert payload["dry_run"] is True
    assert payload["env_written"] is False
    assert payload["database_path"] == str(
        hermes_home / "alexandria-hermes" / "data" / "alexandria_hermes.db"
    )
    assert str(payload["database_url"]).startswith("sqlite+aiosqlite:////")
    assert "postgres" not in json.dumps(payload).lower()
    assert not (hermes_home / "alexandria-hermes" / ".env").exists()


def test_setup_backend_daemon_apply_writes_env_and_guidebook(
    tmp_path: Path,
) -> None:
    """Backend-daemon setup writes generated env and guidebook when applied."""
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()

    exit_code, payload, stderr = _json_stdout(
        [
            "setup",
            "--mode",
            "backend-daemon",
            "--hermes-home",
            str(hermes_home),
            "--apply",
            "--write-guidebook",
            "--operator-api-key",
            "test-operator-api-key-for-setup-000000000000",
        ]
    )

    env_path = hermes_home / "alexandria-hermes" / ".env"
    guidebook_path = hermes_home / "alexandria-hermes" / "GUIDEBOOK.md"
    env_text = env_path.read_text(encoding="utf-8")
    assert exit_code == 0, stderr
    assert payload["env_written"] is True
    assert payload["guidebook_written"] is True
    assert payload["env_path"] == str(env_path)
    assert payload["guidebook_path"] == str(guidebook_path)
    assert (
        "ALEXANDRIA_OPERATOR_API_KEY=test-operator-api-key-for-setup-000000000000"
        in env_text
    )
    assert "DATABASE_URL=sqlite+aiosqlite:///" in env_text
    assert "POSTGRES" not in env_text.upper()
    assert "Backend + SQLite daemon" in guidebook_path.read_text(encoding="utf-8")


def test_setup_fullstack_compose_reports_compose_next_step(tmp_path: Path) -> None:
    """Full-stack compose remains a first-class setup mode."""
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()

    exit_code, payload, stderr = _json_stdout(
        [
            "setup",
            "--mode",
            "fullstack-compose",
            "--hermes-home",
            str(hermes_home),
            "--dry-run",
        ]
    )

    next_steps = "\n".join(str(step) for step in payload["next_steps"])
    assert exit_code == 0, stderr
    assert payload["mode"] == "fullstack-compose"
    assert "docker compose up --build" in next_steps
    assert "demo-only" not in next_steps.lower()


def test_setup_invalid_runtime_mode_is_rejected() -> None:
    """Runtime mode choices do not include unsupported database variants."""
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = run(
        ["setup", "--mode", "postgres", "--dry-run"],
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code != 0
    assert "postgres" in stderr.getvalue()
