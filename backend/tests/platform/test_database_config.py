"""Database runtime configuration contracts."""

from __future__ import annotations

import pytest
from app.platform.config.database_config import DatabaseConfig
from pydantic import ValidationError


@pytest.mark.parametrize("scheme", ["postgresql", "postgres"])
def test_database_config_normalizes_generic_postgres_urls(scheme: str) -> None:
    """Generic PostgreSQL URLs should use the installed asyncpg driver."""
    config = DatabaseConfig(
        _env_file=None,
        url=f"{scheme}://database-user@postgres/alexandria",
    )

    assert config.url == "postgresql+asyncpg://database-user@postgres/alexandria"


def test_database_config_preserves_explicit_async_urls() -> None:
    """Already explicit async SQLAlchemy URLs should remain unchanged."""
    config = DatabaseConfig(
        _env_file=None,
        url="postgresql+asyncpg://database-user@postgres/alexandria",
    )

    assert config.url == "postgresql+asyncpg://database-user@postgres/alexandria"


def test_database_config_rejects_blank_urls() -> None:
    """A blank database URL must fail at the external settings boundary."""
    with pytest.raises(ValidationError, match="database URL must not be blank"):
        DatabaseConfig(_env_file=None, url="   ")
