"""Redis configuration contracts."""

from __future__ import annotations

import pytest
from app.platform.config.redis_config import RedisConfig
from pydantic import ValidationError


def test_redis_config_is_disabled_by_default() -> None:
    """Redis must remain optional outside explicitly configured deployments."""
    config = RedisConfig(_env_file=None)

    assert config.url is None
    assert config.operational_readiness_ttl_seconds == 5


def test_redis_config_normalizes_blank_url_to_disabled() -> None:
    """Blank optional URL values should not create a partially enabled client."""
    config = RedisConfig(_env_file=None, url="   ")

    assert config.url is None


@pytest.mark.parametrize("ttl_seconds", [0, 31])
def test_redis_config_rejects_out_of_range_ttl(ttl_seconds: int) -> None:
    """Readiness caching must remain short lived and finite."""
    with pytest.raises(ValidationError):
        RedisConfig(
            _env_file=None,
            operational_readiness_ttl_seconds=ttl_seconds,
        )
