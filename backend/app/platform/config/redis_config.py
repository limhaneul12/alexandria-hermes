"""Optional Redis cache, queue, and rate-limit settings."""

from __future__ import annotations

from app.shared.utils.config import settings_model_config
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class RedisConfig(BaseSettings):
    """Redis remains removable infrastructure, never canonical storage."""

    model_config = settings_model_config(env_prefix="SERVICE_REDIS_")

    url: str | None = Field(default=None, min_length=1, repr=False)
    max_connections: int = Field(default=8, ge=1, le=64)

    operational_readiness_ttl_seconds: int = Field(default=5, ge=1, le=30)
    graph_status_ttl_seconds: int = Field(default=5, ge=1, le=30)
    embedding_health_ttl_seconds: int = Field(default=10, ge=1, le=60)

    maintenance_queue_enabled: bool = Field(default=True)
    maintenance_worker_concurrency: int = Field(default=1, ge=1, le=4)
    maintenance_poll_interval_ms: int = Field(default=250, ge=50, le=5_000)
    maintenance_claim_idle_ms: int = Field(
        default=30 * 60 * 1_000,
        ge=60_000,
        le=24 * 60 * 60 * 1_000,
    )
    maintenance_job_max_attempts: int = Field(default=3, ge=1, le=10)
    maintenance_job_status_ttl_seconds: int = Field(
        default=24 * 60 * 60,
        ge=60,
        le=7 * 24 * 60 * 60,
    )
    maintenance_stream_max_length: int = Field(default=10_000, ge=100, le=100_000)
    maintenance_manual_cooldown_seconds: int = Field(default=30, ge=1, le=3_600)
    maintenance_scheduler_cooldown_seconds: int = Field(
        default=5 * 60,
        ge=1,
        le=24 * 60 * 60,
    )

    external_api_rate_limit: int = Field(default=60, ge=1, le=10_000)
    external_api_rate_window_seconds: int = Field(default=60, ge=1, le=3_600)

    @field_validator("url", mode="before")
    @classmethod
    def normalize_optional_url(cls, value: str | None) -> str | None:
        """Normalize optional Redis URL text without enabling Redis implicitly.

        Args:
            value: Raw optional Redis URL from the settings boundary.

        Returns:
            Trimmed URL, or None when Redis remains disabled.
        """
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value
