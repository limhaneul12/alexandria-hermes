"""Common service configuration model.

This module reads shared service configuration from ``.env`` and environment
variables. All fields use the ``SERVICE_`` prefix.
"""

from __future__ import annotations

from typing import Literal

from app.shared.util.config import settings_model_config
from pydantic import Field
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
