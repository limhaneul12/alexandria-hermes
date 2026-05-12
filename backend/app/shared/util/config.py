"""Shared helper for building common settings model configuration."""

from __future__ import annotations

from pydantic_settings import SettingsConfigDict


def settings_model_config(*, env_prefix: str) -> SettingsConfigDict:
    """Build a shared ``SettingsConfigDict`` based on environment variable prefix.

    Args:
        env_prefix: Environment variable prefix such as ``SERVICE_`` or ``STREAM_``.

    Return:
        Settings config dictionary that supports loading from ``.env``.
    """
    return SettingsConfigDict(
        env_prefix=env_prefix,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
