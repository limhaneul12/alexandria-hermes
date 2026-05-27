"""Tests for service configuration defaults."""

from __future__ import annotations

import pytest
from app.platform.config.app_config import AppConfig


def test_app_config_uses_hermes_codex_oauth_defaults_when_env_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Codex OAuth metadata should not be required in local env files."""
    monkeypatch.delenv("SERVICE_CODEX_OAUTH_ISSUER", raising=False)
    monkeypatch.delenv("SERVICE_CODEX_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.delenv("SERVICE_CODEX_OAUTH_DEVICE_EXPIRES_IN_SECONDS", raising=False)
    monkeypatch.delenv("SERVICE_CODEX_OAUTH_MIN_POLL_INTERVAL_SECONDS", raising=False)

    config = AppConfig(
        _env_file=None,
        operator_api_key="x" * 32,
    )

    expected = {
        "issuer": "https://auth.openai.com",
        "client_id": "app_EMoamEEZ73f0CkXaXp7hrann",
        "device_expires_in_seconds": 900,
        "min_poll_interval_seconds": 3,
        "obsidian_vault_config_path": "./data/obsidian-vault-config.json",
        "langgraph_checkpoint_path": "./data/obsidian_librarian_langgraph.sqlite",
    }
    actual = {
        "issuer": config.codex_oauth_issuer,
        "client_id": config.codex_oauth_client_id,
        "device_expires_in_seconds": config.codex_oauth_device_expires_in_seconds,
        "min_poll_interval_seconds": config.codex_oauth_min_poll_interval_seconds,
        "obsidian_vault_config_path": config.obsidian_vault_config_path,
        "langgraph_checkpoint_path": (
            config.obsidian_librarian_langgraph_checkpoint_path
        ),
    }

    assert actual == expected


def test_app_config_keeps_codex_oauth_env_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Operators should still be able to override public OAuth metadata locally."""
    monkeypatch.setenv("SERVICE_CODEX_OAUTH_ISSUER", "https://auth.openai.com")
    monkeypatch.setenv("SERVICE_CODEX_OAUTH_CLIENT_ID", "custom-client-id")
    monkeypatch.setenv("SERVICE_CODEX_OAUTH_DEVICE_EXPIRES_IN_SECONDS", "600")
    monkeypatch.setenv("SERVICE_CODEX_OAUTH_MIN_POLL_INTERVAL_SECONDS", "5")
    monkeypatch.setenv(
        "SERVICE_OBSIDIAN_LIBRARIAN_LANGGRAPH_CHECKPOINT_PATH",
        "/tmp/langgraph.sqlite",
    )

    config = AppConfig(
        _env_file=None,
        operator_api_key="x" * 32,
    )

    assert config.codex_oauth_issuer == "https://auth.openai.com"
    assert config.codex_oauth_client_id == "custom-client-id"
    assert config.codex_oauth_device_expires_in_seconds == 600
    assert config.codex_oauth_min_poll_interval_seconds == 5
    assert config.obsidian_librarian_langgraph_checkpoint_path == (
        "/tmp/langgraph.sqlite"
    )


def test_app_config_reads_operator_key_from_alexandria_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The shared operator secret should use the Alexandria env name."""
    expected_key = "alexandria-operator-key-for-local-single-operator"
    monkeypatch.setenv("ALEXANDRIA_OPERATOR_API_KEY", expected_key)

    config = AppConfig(_env_file=None)

    assert config.operator_api_key.get_secret_value() == expected_key
