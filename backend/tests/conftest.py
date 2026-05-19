"""Shared backend test configuration."""

from __future__ import annotations

import os

os.environ.setdefault(
    "ALEXANDRIA_OPERATOR_API_KEY",
    "test-operator-api-key-for-route-contracts-000000000000",
)

from app.main import app
from app.platform.security.operator_api_key import (
    require_operator_api_key,
)


async def allow_operator_api_key_for_tests() -> None:
    """Bypass operator auth for tests that do not cover auth behavior.

    Returns:
        None.
    """
    return None


app.dependency_overrides[require_operator_api_key] = allow_operator_api_key_for_tests
