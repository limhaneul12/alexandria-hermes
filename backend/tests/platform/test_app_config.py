"""Tests for service configuration defaults."""

from __future__ import annotations

import pytest
from app.platform.config.app_config import AppConfig
from pydantic import ValidationError


def test_app_config_uses_hermes_codex_oauth_defaults_when_env_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Codex OAuth metadata should not be required in local env files."""
    monkeypatch.delenv("SERVICE_CODEX_OAUTH_ISSUER", raising=False)
    monkeypatch.delenv("SERVICE_CODEX_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.delenv("SERVICE_CODEX_OAUTH_DEVICE_EXPIRES_IN_SECONDS", raising=False)
    monkeypatch.delenv("SERVICE_CODEX_OAUTH_MIN_POLL_INTERVAL_SECONDS", raising=False)

    config = AppConfig(_env_file=None)

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

    config = AppConfig(_env_file=None)

    assert config.codex_oauth_issuer == "https://auth.openai.com"
    assert config.codex_oauth_client_id == "custom-client-id"
    assert config.codex_oauth_device_expires_in_seconds == 600
    assert config.codex_oauth_min_poll_interval_seconds == 5
    assert config.obsidian_librarian_langgraph_checkpoint_path == (
        "/tmp/langgraph.sqlite"
    )


def test_app_config_defaults_mcp_auth_to_no_auth() -> None:
    """ChatGPT developer-mode MCP connections should not require custom headers."""
    config = AppConfig(_env_file=None)

    assert config.mcp_auth_mode == "none"
    assert config.mcp_transport_host == "0.0.0.0"
    assert config.mcp_oauth_required_scopes() == ("alexandria:mcp",)


def test_app_config_disables_graph_read_model_when_env_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The backend must not opt into an external graph read model by default."""
    monkeypatch.delenv("SERVICE_GRAPH_READ_MODEL", raising=False)

    config = AppConfig(_env_file=None)

    assert config.graph_read_model == "disabled"


def test_app_config_disables_automatic_embedding_recovery_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Long-running embedding recovery must require an explicit operator opt-in."""
    monkeypatch.delenv("SERVICE_RAG_EMBEDDING_RECOVERY_ON_STARTUP", raising=False)
    monkeypatch.delenv(
        "SERVICE_RAG_EMBEDDING_RECOVERY_ON_VAULT_REINDEX",
        raising=False,
    )

    config = AppConfig(_env_file=None)

    assert config.rag_embedding_recovery_on_startup is False
    assert config.rag_embedding_recovery_on_vault_reindex is False


def test_app_config_allows_explicit_automatic_embedding_recovery_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Operators may explicitly enable either automatic recovery path."""
    monkeypatch.setenv("SERVICE_RAG_EMBEDDING_RECOVERY_ON_STARTUP", "true")
    monkeypatch.setenv(
        "SERVICE_RAG_EMBEDDING_RECOVERY_ON_VAULT_REINDEX",
        "true",
    )

    config = AppConfig(_env_file=None)

    assert config.rag_embedding_recovery_on_startup is True
    assert config.rag_embedding_recovery_on_vault_reindex is True


def test_app_config_defaults_embedding_threads_and_allows_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Local E5 inference should use a balanced default with an operator override."""
    monkeypatch.delenv("SERVICE_RAG_EMBEDDING_THREADS", raising=False)

    assert AppConfig(_env_file=None).rag_embedding_threads == 4

    monkeypatch.setenv("SERVICE_RAG_EMBEDDING_THREADS", "6")

    assert AppConfig(_env_file=None).rag_embedding_threads == 6


def test_app_config_accepts_neo4j_graph_read_model_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Operators may explicitly select the optional Neo4j projection target."""
    monkeypatch.setenv("SERVICE_GRAPH_READ_MODEL", "neo4j")
    monkeypatch.setenv("SERVICE_NEO4J_URI", "neo4j://127.0.0.1:7687")
    monkeypatch.setenv("SERVICE_NEO4J_USERNAME", "neo4j")
    monkeypatch.setenv("SERVICE_NEO4J_PASSWORD", "test-only-secret")

    config = AppConfig(_env_file=None)

    assert config.graph_read_model == "neo4j"


def test_app_config_requires_consumed_neo4j_connection_settings_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Neo4j selection should fail closed until the adapter can authenticate."""
    monkeypatch.setenv("SERVICE_GRAPH_READ_MODEL", "neo4j")
    monkeypatch.delenv("SERVICE_NEO4J_URI", raising=False)
    monkeypatch.delenv("SERVICE_NEO4J_USERNAME", raising=False)
    monkeypatch.delenv("SERVICE_NEO4J_PASSWORD", raising=False)

    with pytest.raises(ValidationError, match="Neo4j graph read model requires"):
        AppConfig(_env_file=None)


def test_app_config_rejects_blank_neo4j_connection_settings_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Whitespace-only Neo4j settings should fail closed before driver creation."""
    monkeypatch.setenv("SERVICE_GRAPH_READ_MODEL", "neo4j")
    monkeypatch.setenv("SERVICE_NEO4J_URI", "   ")
    monkeypatch.setenv("SERVICE_NEO4J_USERNAME", "\t")
    monkeypatch.setenv("SERVICE_NEO4J_PASSWORD", "  ")

    with pytest.raises(ValidationError, match="Neo4j graph read model requires"):
        AppConfig(_env_file=None)


def test_app_config_trims_neo4j_connection_settings_when_enabled() -> None:
    """Neo4j connection text should be normalized at the settings boundary."""
    config = AppConfig(
        _env_file=None,
        graph_read_model="neo4j",
        neo4j_uri=" bolt://127.0.0.1:7687 ",
        neo4j_username=" neo4j ",
        neo4j_password=" test-only-secret ",
        neo4j_database=" neo4j ",
    )

    assert config.neo4j_uri == "bolt://127.0.0.1:7687"
    assert config.neo4j_username == "neo4j"
    assert config.neo4j_password_value() == "test-only-secret"
    assert config.neo4j_database == "neo4j"


def test_app_config_keeps_neo4j_password_secret_out_of_repr() -> None:
    """Connection credentials must not appear in settings diagnostics."""
    config = AppConfig(
        _env_file=None,
        graph_read_model="neo4j",
        neo4j_uri="neo4j://127.0.0.1:7687",
        neo4j_username="neo4j",
        neo4j_password="test-only-secret",
    )

    assert config.neo4j_database == "neo4j"
    assert "neo4j://127.0.0.1:7687" not in repr(config)
    assert "neo4j_username" not in repr(config)
    assert "test-only-secret" not in repr(config)


def test_app_config_keeps_memory_relation_model_provider_opt_in() -> None:
    """Memory relation model execution must remain disabled until configured."""
    config = AppConfig(_env_file=None)

    assert config.memory_reconciliation_provider_id is None
    assert config.memory_reconciliation_model == "gpt-5.5"
    assert config.memory_reconciliation_provider_timeout_seconds == 30.0


def test_app_config_normalizes_memory_relation_provider_settings() -> None:
    """Only non-secret provider selection settings belong in AppConfig."""
    config = AppConfig(
        _env_file=None,
        memory_reconciliation_provider_id=" openai-memory ",
        memory_reconciliation_model=" provider-fallback ",
        memory_reconciliation_provider_timeout_seconds=15.5,
    )

    assert config.memory_reconciliation_provider_id == "openai-memory"
    assert config.memory_reconciliation_model == "provider-fallback"
    assert config.memory_reconciliation_provider_timeout_seconds == 15.5


def test_app_config_rejects_incomplete_mcp_oauth_config() -> None:
    """OAuth mode should fail closed when issuer metadata is missing."""
    with pytest.raises(ValueError, match="MCP OAuth mode requires"):
        AppConfig(_env_file=None, mcp_auth_mode="oauth2")


def test_app_config_accepts_complete_mcp_oauth_config() -> None:
    """OAuth mode should normalize resource-server metadata settings."""
    config = AppConfig(
        _env_file=None,
        mcp_auth_mode="oauth2",
        mcp_oauth_issuer="https://auth.example.com",
        mcp_oauth_audience="https://mcp.example.com/mcp",
        mcp_oauth_jwks_url="https://auth.example.com/.well-known/jwks.json",
        mcp_oauth_authorization_servers=(
            "https://auth.example.com, https://backup.example.com"
        ),
        mcp_oauth_required_scope="alexandria:mcp alexandria:read",
    )

    assert config.mcp_oauth_authorization_server_urls() == (
        "https://auth.example.com",
        "https://backup.example.com",
    )
    assert config.mcp_oauth_required_scopes() == (
        "alexandria:mcp",
        "alexandria:read",
    )
