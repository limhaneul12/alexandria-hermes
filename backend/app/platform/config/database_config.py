"""Database configuration model."""

from __future__ import annotations

from app.shared.util.config import settings_model_config
from pydantic import Field
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseSettings):
    """Database runtime settings for SQLAlchemy persistence."""

    model_config = settings_model_config(env_prefix="DATABASE_")

    url: str = Field(
        default="sqlite+aiosqlite:///./data/alexandria_hermes.db",
        description="Async SQLAlchemy database URL.",
    )
