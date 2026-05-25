"""Behavior tests for local Obsidian plugin installation."""

from __future__ import annotations

import io
from pathlib import Path

from app.cli import run
from app.shared.serialization.orjson_codec import loads_json


def test_obsidian_install_local_copies_plugin_and_enables_it(tmp_path: Path) -> None:
    """install-local should default to copy mode to avoid repo data.json writes."""
    vault = tmp_path / "Alexandria"
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = run(
        [
            "--json",
            "obsidian",
            "install-local",
            "--vault-path",
            str(vault),
        ],
        stdout=stdout,
        stderr=stderr,
    )

    payload = loads_json(stdout.getvalue())
    target = Path(str(payload["plugin_target"]))
    community_plugins = loads_json(
        (vault / ".obsidian" / "community-plugins.json").read_text(encoding="utf-8")
    )
    app_json = loads_json(
        (vault / ".obsidian" / "app.json").read_text(encoding="utf-8")
    )
    assert exit_code == 0, stderr.getvalue()
    assert payload["plugin_install_mode"] == "copy"
    assert target.exists()
    assert not target.is_symlink()
    assert (target / "main.js").exists()
    assert "alexandria-librarian" in community_plugins
    assert app_json["safeMode"] is False


def test_obsidian_install_local_removes_stale_files_but_keeps_data(
    tmp_path: Path,
) -> None:
    """copy mode should refresh plugin code without deleting vault-local settings."""
    vault = tmp_path / "Alexandria"
    target = vault / ".obsidian" / "plugins" / "alexandria-librarian"
    target.mkdir(parents=True)
    stale_file = target / "stale.js"
    data_file = target / "data.json"
    stale_file.write_text("old", encoding="utf-8")
    data_file.write_text('{"backendUrl":"local"}', encoding="utf-8")

    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = run(
        [
            "--json",
            "obsidian",
            "install-local",
            "--vault-path",
            str(vault),
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0, stderr.getvalue()
    assert not stale_file.exists()
    assert data_file.read_text(encoding="utf-8") == '{"backendUrl":"local"}'
    assert (target / "main.js").exists()
