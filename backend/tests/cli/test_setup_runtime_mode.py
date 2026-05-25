"""Behavior tests for Alexandria runtime setup modes."""

from __future__ import annotations

import io
from pathlib import Path

from app.cli import run
from app.shared.serialization.orjson_codec import dumps_json, loads_json


def _json_stdout(argv: list[str]) -> tuple[int, dict[str, object], str]:
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = run(["--json", *argv], stdout=stdout, stderr=stderr)

    payload = loads_json(stdout.getvalue()) if stdout.getvalue().strip() else {}
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
    assert payload["obsidian_vault_path"] == str(
        hermes_home / "alexandria-hermes" / "data" / "obsidian-vault"
    )
    assert payload["alexandria_obsidian_root"] == "Alexandria"
    assert str(payload["database_url"]).startswith("sqlite+aiosqlite:////")
    assert "postgres" not in dumps_json(payload).decode().lower()
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
    assert "SERVICE_OBSIDIAN_VAULT_PATH=" in env_text
    assert "SERVICE_ALEXANDRIA_OBSIDIAN_ROOT=Alexandria" in env_text
    assert "SERVICE_MEMORY_COMPACT_NOTE_DIR=Alexandria/Memory Compacts" in env_text
    assert "POSTGRES" not in env_text.upper()
    guidebook_text = guidebook_path.read_text(encoding="utf-8")
    assert "Backend + SQLite daemon" in guidebook_text
    assert "alexandria-hermes obsidian init" in guidebook_text


def test_setup_backend_daemon_targets_existing_obsidian_vault_root(
    tmp_path: Path,
) -> None:
    """Setup can attach Alexandria directly to an existing Obsidian vault."""
    hermes_home = tmp_path / "hermes"
    vault_path = tmp_path / "Alexandria"
    hermes_home.mkdir()

    exit_code, payload, stderr = _json_stdout(
        [
            "setup",
            "--mode",
            "backend-daemon",
            "--hermes-home",
            str(hermes_home),
            "--obsidian-vault-path",
            str(vault_path),
            "--alexandria-obsidian-root",
            ".",
            "--apply",
            "--write-guidebook",
            "--operator-api-key",
            "test-operator-api-key-for-setup-000000000000",
        ]
    )

    env_path = hermes_home / "alexandria-hermes" / ".env"
    guidebook_path = hermes_home / "alexandria-hermes" / "GUIDEBOOK.md"
    env_text = env_path.read_text(encoding="utf-8")
    guidebook_text = guidebook_path.read_text(encoding="utf-8")
    assert exit_code == 0, stderr
    assert vault_path.exists()
    assert payload["obsidian_vault_path"] == str(vault_path.resolve())
    assert payload["alexandria_obsidian_root"] == "."
    assert f"SERVICE_OBSIDIAN_VAULT_PATH={vault_path.resolve()}" in env_text
    assert "SERVICE_ALEXANDRIA_OBSIDIAN_ROOT=." in env_text
    assert "SERVICE_MEMORY_COMPACT_NOTE_DIR=Memory Compacts" in env_text
    assert "Alexandria root in vault: `.`" in guidebook_text
    assert "`SERVICE_ALEXANDRIA_OBSIDIAN_ROOT=.`" in guidebook_text


def test_setup_guidebook_only_reports_planning_next_step(tmp_path: Path) -> None:
    """Guidebook-only remains a supported planning mode after frontend removal."""
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()

    exit_code, payload, stderr = _json_stdout(
        [
            "setup",
            "--mode",
            "guidebook-only",
            "--hermes-home",
            str(hermes_home),
            "--dry-run",
        ]
    )

    next_steps = "\n".join(str(step) for step in payload["next_steps"])
    assert exit_code == 0, stderr
    assert payload["mode"] == "guidebook-only"
    assert "choose a runtime mode" in next_steps
    assert "frontend" not in next_steps.lower()


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


def test_setup_backend_daemon_run_migrations_creates_obsidian_tables(
    tmp_path: Path,
) -> None:
    """--run-migrations should prevent first Obsidian init from missing tables."""
    import sqlite3

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
            "--run-migrations",
            "--operator-api-key",
            "test-operator-api-key-for-setup-000000000000",
        ]
    )

    database_path = Path(str(payload["database_path"]))
    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type in ('table', 'virtual table')"
            )
        }
    assert exit_code == 0, stderr
    assert payload["migrations"] == {
        "run_requested": True,
        "status": "upgraded",
        "revision": "head",
    }
    assert "obsidian_files" in table_names
    assert "obsidian_edges" in table_names
