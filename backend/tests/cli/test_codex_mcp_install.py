"""Behavior tests for Codex MCP installation support."""

from __future__ import annotations

import io
from pathlib import Path

from app.cli import run
from app.shared.serialization.orjson_codec import loads_json
from app.shared.types.extra_types import JSONObject


def _json_object(value: str) -> JSONObject:
    payload = loads_json(value)
    assert isinstance(payload, dict)
    return payload


def test_codex_install_mcp_dry_run_plans_config_without_writing_secret(
    tmp_path: Path,
) -> None:
    """Codex MCP dry-run should preview config and redact operator secrets."""
    codex_home = tmp_path / "codex"
    codex_home.mkdir()
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "codex",
            "install-mcp",
            "--codex-home",
            str(codex_home),
            "--api-url",
            "http://backend:8000",
            "--operator-api-key",
            "secret-token",
            "--dry-run",
        ],
        stdout=stdout,
    )

    output = stdout.getvalue()
    payload = _json_object(output)
    server = payload["mcp_server"]
    assert isinstance(server, dict)
    assert exit_code == 0
    assert {key: payload[key] for key in ("dry_run", "config_path")} == {
        "dry_run": True,
        "config_path": str(codex_home / "config.toml"),
    }
    assert server["command"] == "alexandria-hermes"
    assert server["args"] == ["mcp", "serve"]
    assert server["env"] == {
        "ALEXANDRIA_API_URL": "http://backend:8000",
        "ALEXANDRIA_OPERATOR_API_KEY": "<REDACTED>",
    }
    assert "secret-token" not in output
    assert not (codex_home / "config.toml").exists()


def test_codex_install_mcp_writes_managed_config_without_removing_existing_servers(
    tmp_path: Path,
) -> None:
    """Codex MCP install should add a managed Alexandria server block."""
    codex_home = tmp_path / "codex"
    codex_home.mkdir()
    config_path = codex_home / "config.toml"
    config_path.write_text(
        'model = "gpt-5.5"\n\n[mcp_servers.playwright]\ncommand = "npx"\n',
        encoding="utf-8",
    )
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "codex",
            "install-mcp",
            "--codex-home",
            str(codex_home),
            "--api-url",
            "http://backend:8000",
        ],
        stdout=stdout,
    )

    payload = _json_object(stdout.getvalue())
    config = config_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert payload["written"] == ["config.toml"]
    assert payload["backups"] == ["config.toml.bak"]
    assert 'model = "gpt-5.5"' in config
    assert "[mcp_servers.playwright]" in config
    assert "# BEGIN Alexandria-Hermes Codex MCP" in config
    assert "[mcp_servers.alexandria]" in config
    assert 'command = "alexandria-hermes"' in config
    assert 'args = ["mcp", "serve"]' in config
    assert "[mcp_servers.alexandria.env]" in config
    assert 'ALEXANDRIA_API_URL = "http://backend:8000"' in config


def test_codex_install_mcp_skips_unmanaged_existing_server_without_overwrite(
    tmp_path: Path,
) -> None:
    """Codex MCP install should not replace an unmanaged Alexandria server."""
    codex_home = tmp_path / "codex"
    codex_home.mkdir()
    config_path = codex_home / "config.toml"
    original = '[mcp_servers.alexandria]\ncommand = "custom-alexandria"\n'
    config_path.write_text(original, encoding="utf-8")
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "codex",
            "install-mcp",
            "--codex-home",
            str(codex_home),
            "--dry-run",
        ],
        stdout=stdout,
    )

    payload = _json_object(stdout.getvalue())
    assert exit_code == 0
    assert payload["written"] == []
    assert payload["skipped"] == ["config.toml"]
    assert config_path.read_text(encoding="utf-8") == original


def test_codex_install_mcp_overwrite_replaces_unmanaged_existing_server(
    tmp_path: Path,
) -> None:
    """Codex MCP overwrite should replace only the Alexandria MCP tables."""
    codex_home = tmp_path / "codex"
    codex_home.mkdir()
    config_path = codex_home / "config.toml"
    config_path.write_text(
        '[mcp_servers.alexandria]\ncommand = "custom-alexandria"\n\n'
        '[mcp_servers.alexandria.env]\nOLD = "1"\n\n'
        '[mcp_servers.other]\ncommand = "other"\n',
        encoding="utf-8",
    )
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "codex",
            "install-mcp",
            "--codex-home",
            str(codex_home),
            "--overwrite",
        ],
        stdout=stdout,
    )

    payload = _json_object(stdout.getvalue())
    config = config_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert payload["written"] == ["config.toml"]
    assert payload["backups"] == ["config.toml.bak"]
    assert "custom-alexandria" not in config
    assert 'OLD = "1"' not in config
    assert "[mcp_servers.other]" in config
    assert "[mcp_servers.alexandria]" in config
