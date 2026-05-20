"""Behavior tests for setup guidebook generation."""

from __future__ import annotations

import io
from pathlib import Path

from app.cli import run
from app.shared.serialization.orjson_codec import loads_json


def test_setup_guidebook_documents_runtime_and_policy_controls(tmp_path: Path) -> None:
    """Generated guidebook includes mode-specific commands and opt-out controls."""
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "setup",
            "--mode",
            "backend-daemon",
            "--hermes-home",
            str(hermes_home),
            "--apply",
            "--write-guidebook",
            "--operator-api-key",
            "test-operator-api-key-for-guidebook-000000000000",
        ],
        stdout=stdout,
    )

    payload = loads_json(stdout.getvalue())
    guidebook_path = Path(str(payload["guidebook_path"]))
    guidebook = guidebook_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert "Backend + SQLite daemon" in guidebook
    assert str(hermes_home / "alexandria-hermes" / ".env") in guidebook
    assert "alexandria-hermes hermes policy disable" in guidebook
    assert "alexandria-hermes hermes onboard" in guidebook
