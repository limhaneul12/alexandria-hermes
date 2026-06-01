"""Behavior tests for the foreground backend serve command."""

from __future__ import annotations

import io

from app.cli import run


def test_serve_help_documents_backend_sqlite_options() -> None:
    """Serve help exposes env/host/port and backend-only SQLite language."""
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = run(["serve", "--help"], stdout=stdout, stderr=stderr)

    help_text = stdout.getvalue()
    assert exit_code == 0, stderr.getvalue()
    assert "--env-file" in help_text
    assert "--host" in help_text
    assert "--port" in help_text
    assert "SQLite" in help_text
    assert "backend" in help_text.lower()


def test_health_cli_calls_live_endpoint() -> None:
    """Health command should stay wired after pruning the stale library handler name."""
    stdout = io.StringIO()
    stderr = io.StringIO()
    calls: list[tuple[str, str]] = []

    def transport(method, url, body, headers, timeout):
        calls.append((method, url))
        return 200, b'{"status":"ok"}'

    exit_code = run(["health"], transport=transport, stdout=stdout, stderr=stderr)

    assert exit_code == 0, stderr.getvalue()
    assert calls == [("GET", "http://localhost:8000/health/live")]
    assert "Hermes backend is reachable" in stdout.getvalue()
