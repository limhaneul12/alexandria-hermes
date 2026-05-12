"""Redis Stream runtime settings for event ingestion."""

from __future__ import annotations

from typing import Literal

from app.shared.util.config import settings_model_config
from pydantic import Field
from pydantic_settings import BaseSettings

DEFAULT_REDIS_URL = "redis://localhost:6379/0"


class StreamConfig(BaseSettings):
    """Redis Stream consumer settings.

    Role:
        Reads runtime values that vary by deployment, such as Redis endpoint,
        Redis deployment mode, and consumer batch/read settings.
    """

    model_config = settings_model_config(env_prefix="STREAM_")

    redis_url: str = Field(default=DEFAULT_REDIS_URL)
    redis_mode: Literal["single", "cluster"] = Field(default="single")
    batch_size: int = Field(default=100, ge=1)
    block_ms: int = Field(default=1000, ge=1)

    @property
    def redis_urls(self) -> tuple[str, ...]:
        """Return comma-separated Redis URLs as a normalized tuple.

        Args:
            None.

        Return:
            Normalized Redis URL tuple. Empty input falls back to the local default.
        """
        urls = tuple(url.strip() for url in self.redis_url.split(",") if url.strip())
        if urls:
            return urls
        return (DEFAULT_REDIS_URL,)
