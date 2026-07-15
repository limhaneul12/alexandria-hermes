"""Common service configuration model.

This module reads shared service configuration from ``.env`` and environment
variables. Most service fields use the ``SERVICE_`` prefix.
"""

from __future__ import annotations

from typing import Final, Literal

from app.mcp_server.type_validate.auth_contracts import McpAuthMode
from app.memory.application.retrieval.embedding_factory import EmbeddingProviderName
from app.memory.application.retrieval.embedding_provider import (
    DEFAULT_EMBEDDING_DIMENSIONS,
    DEFAULT_EMBEDDING_MODEL,
)
from app.shared.utils.config import settings_model_config
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings

DEFAULT_CODEX_OAUTH_ISSUER: Final[str] = "https://auth.openai.com"
DEFAULT_CODEX_OAUTH_CLIENT_ID: Final[str] = "app_EMoamEEZ73f0CkXaXp7hrann"
DEFAULT_CODEX_OAUTH_DEVICE_EXPIRES_IN_SECONDS: Final[int] = 900
DEFAULT_CODEX_OAUTH_MIN_POLL_INTERVAL_SECONDS: Final[int] = 3


class AppConfig(BaseSettings):
    """Common service settings model.

    Role:
        Centralizes global service settings such as app name, environment, version,
        and log level.
    """

    model_config = {
        **settings_model_config(env_prefix="SERVICE_"),
        "populate_by_name": True,
    }

    # Service identifier used by logs and operational tooling.
    app_name: str = Field(default="alexandria-hermes")
    # Runtime environment. Only ``local``, ``stage``, and ``prod`` are allowed.
    app_env: Literal["local", "stage", "prod"] = Field(default="local")
    # Service version string.
    app_version: str = Field(default="0.1.0")
    # Python logging level name.
    app_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    # 32-byte URL-safe base64 key or passphrase used to encrypt provider secrets at rest.
    secret_encryption_key: str | None = Field(default=None)
    # Host value passed to FastMCP transport settings. Use 0.0.0.0 for reverse tunnels.
    mcp_transport_host: str = Field(default="0.0.0.0", min_length=1)
    # Public MCP authentication mode for ChatGPT Apps/Connectors.
    mcp_auth_mode: McpAuthMode = Field(default=McpAuthMode.NONE)
    # OAuth issuer expected in ChatGPT MCP Bearer tokens when MCP auth is oauth2.
    mcp_oauth_issuer: str | None = Field(default=None)
    # OAuth audience/resource expected in ChatGPT MCP Bearer tokens.
    mcp_oauth_audience: str | None = Field(default=None)
    # JWKS endpoint used to verify ChatGPT MCP Bearer token signatures.
    mcp_oauth_jwks_url: str | None = Field(default=None)
    # Public MCP resource URL advertised in protected-resource metadata.
    mcp_oauth_resource: str | None = Field(default=None)
    # Comma-separated OAuth authorization-server metadata URLs.
    mcp_oauth_authorization_servers: str | None = Field(default=None)
    # Space-separated scopes required for ChatGPT MCP Bearer tokens.
    mcp_oauth_required_scope: str = Field(default="alexandria:mcp")
    # OpenAI Codex OAuth issuer used to derive official device-flow endpoints.
    codex_oauth_issuer: str = Field(default=DEFAULT_CODEX_OAUTH_ISSUER, min_length=1)
    # Public OpenAI Codex OAuth client id. This is overridable but not a secret.
    codex_oauth_client_id: str = Field(
        default=DEFAULT_CODEX_OAUTH_CLIENT_ID,
        min_length=1,
    )
    # Pending device authorization lifetime when provider omits expires_in.
    codex_oauth_device_expires_in_seconds: int = Field(
        default=DEFAULT_CODEX_OAUTH_DEVICE_EXPIRES_IN_SECONDS,
        ge=60,
        le=60 * 60,
    )
    # Lower bound for polling interval when provider returns an aggressive value.
    codex_oauth_min_poll_interval_seconds: int = Field(
        default=DEFAULT_CODEX_OAUTH_MIN_POLL_INTERVAL_SECONDS,
        ge=1,
        le=60,
    )
    # Enable local context vector retrieval. FastEmbed remains lazy until embeddings are needed.
    rag_vector_enabled: bool = Field(default=True)
    # Local embedding provider used by context RAG.
    rag_embedding_provider: EmbeddingProviderName = Field(default="fastembed")
    # Local embedding model identifier.
    rag_embedding_model: str = Field(default=DEFAULT_EMBEDDING_MODEL, min_length=1)
    # Embedding vector dimensions expected by the configured model.
    rag_embedding_dimensions: int = Field(default=DEFAULT_EMBEDDING_DIMENSIONS, ge=1)
    # Optional local FastEmbed cache directory.
    rag_embedding_cache_dir: str | None = Field(default=None)
    # Obsidian vault root used as the canonical Markdown storage location.
    obsidian_vault_path: str = Field(default="./data/obsidian-vault", min_length=1)
    # Folder inside the Obsidian vault managed by Alexandria-Hermes.
    alexandria_obsidian_root: str = Field(default="Alexandria", min_length=1)
    # Local JSON override written by the Obsidian plugin when the active vault changes.
    obsidian_vault_config_path: str = Field(
        default="./data/obsidian-vault-config.json",
        min_length=1,
    )
    # Folder inside the Obsidian vault for Memory Compact notes.
    memory_compact_note_dir: str = Field(
        default="Alexandria/Memory Compacts", min_length=1
    )
    # SQLite checkpoint file for LangGraph-powered Obsidian librarian workflows.
    obsidian_librarian_langgraph_checkpoint_path: str = Field(
        default="./data/obsidian_librarian_langgraph.sqlite",
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_mcp_oauth_configuration(self) -> AppConfig:
        """Validate MCP OAuth settings when OAuth mode is enabled.

        Returns:
            Validated app config.
        """
        if self.mcp_auth_mode != McpAuthMode.OAUTH2:
            return self
        missing = [
            name
            for name, value in (
                ("mcp_oauth_issuer", self.mcp_oauth_issuer),
                ("mcp_oauth_audience", self.mcp_oauth_audience),
                ("mcp_oauth_jwks_url", self.mcp_oauth_jwks_url),
            )
            if value is None or not value
        ]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"MCP OAuth mode requires: {joined}")
        return self

    def mcp_oauth_required_scopes(self) -> tuple[str, ...]:
        """Return normalized MCP OAuth scopes from configuration.

        Returns:
            Required scope tuple.
        """
        return tuple(scope for scope in self.mcp_oauth_required_scope.split() if scope)

    def mcp_oauth_authorization_server_urls(self) -> tuple[str, ...]:
        """Return advertised OAuth authorization-server metadata URLs.

        Returns:
            Authorization server URL tuple.
        """
        if self.mcp_oauth_authorization_servers:
            return tuple(
                item.strip()
                for item in self.mcp_oauth_authorization_servers.split(",")
                if item.strip()
            )
        if self.mcp_oauth_issuer:
            return (self.mcp_oauth_issuer,)
        return ()
