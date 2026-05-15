"""Common service configuration model.

This module reads shared service configuration from ``.env`` and environment
variables. All fields use the ``SERVICE_`` prefix.
"""

from __future__ import annotations

from typing import Literal

from app.shared.util.config import settings_model_config
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    """Common service settings model.

    Role:
        Centralizes global service settings such as app name, environment, version,
        and log level.
    """

    model_config = settings_model_config(env_prefix="SERVICE_")

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
    # Operator API key required for sensitive settings/provider operations.
    operator_api_key: SecretStr = Field(min_length=32)
    # OpenAI Codex OAuth issuer used to derive official device-flow endpoints.
    codex_oauth_issuer: str = Field(min_length=1)
    # Public OpenAI Codex OAuth client id. This is configurable but not a secret.
    codex_oauth_client_id: str = Field(min_length=1)
    # Pending device authorization lifetime when provider omits expires_in.
    codex_oauth_device_expires_in_seconds: int = Field(ge=60, le=60 * 60)
    # Lower bound for polling interval when provider returns an aggressive value.
    codex_oauth_min_poll_interval_seconds: int = Field(ge=1, le=60)
