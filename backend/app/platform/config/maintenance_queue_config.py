"""Redis Streams maintenance queue configuration."""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MaintenanceQueueConfig(BaseSettings):
    """Validated process settings for queued embedding maintenance."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SERVICE_REDIS_MAINTENANCE_",
        extra="ignore",
        frozen=True,
        validate_default=True,
    )

    redis_url: str | None = Field(
        default=None,
        validation_alias="SERVICE_REDIS_URL",
        repr=False,
    )
    stream_name: str = "alexandria:maintenance:v1"
    dead_letter_stream_name: str = "alexandria:maintenance:dead:v1"
    consumer_group: str = "alexandria-maintenance-workers-v1"
    status_key_prefix: str = "alexandria:maintenance:job:v1"
    dedup_key_prefix: str = "alexandria:maintenance:dedup:v1"
    rate_key_prefix: str = "alexandria:rate:v1"
    embedding_threads: int = Field(
        default=1,
        validation_alias="SERVICE_RAG_MAINTENANCE_EMBEDDING_THREADS",
        ge=1,
        le=32,
    )
    worker_concurrency: int = Field(default=1, ge=1, le=4)
    batch_limit: int = Field(default=250, ge=1, le=1000)
    max_attempts: int = Field(default=3, ge=1, le=10)
    retry_idle_seconds: int = Field(default=15, ge=1, le=3600)
    block_milliseconds: int = Field(default=2000, ge=100, le=60000)
    status_ttl_seconds: int = Field(default=86400, ge=60, le=604800)
    dedup_cooldown_seconds: int = Field(default=60, ge=1, le=3600)
    submission_limit: int = Field(default=6, ge=1, le=1000)
    submission_window_seconds: int = Field(default=60, ge=1, le=3600)
    max_stream_length: int = Field(default=10000, ge=100, le=1000000)
    worker_max_connections: int = Field(default=2, ge=1, le=16)

    @field_validator("redis_url", mode="before")
    @classmethod
    def normalize_optional_redis_url(cls, value: str | None) -> str | None:
        """Normalize an optional Redis URL without enabling Redis implicitly.

        Args:
            value: Raw Redis URL loaded from settings, or None when disabled.

        Returns:
            Trimmed Redis URL, or None for a missing or blank value.
        """
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None
