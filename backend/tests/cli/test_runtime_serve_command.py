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
