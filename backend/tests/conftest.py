"""Shared backend test configuration."""

from __future__ import annotations

import os

os.environ.setdefault(
    "SERVICE_OPERATOR_API_KEY",
    "test-operator-api-key-for-route-contracts-000000000000",
)
os.environ.setdefault("SERVICE_CODEX_OAUTH_ISSUER", "https://auth.openai.com")
os.environ.setdefault(
    "SERVICE_CODEX_OAUTH_CLIENT_ID",
    "app_EMoamEEZ73f0CkXaXp7hrann",
)
os.environ.setdefault("SERVICE_CODEX_OAUTH_DEVICE_EXPIRES_IN_SECONDS", "900")
os.environ.setdefault("SERVICE_CODEX_OAUTH_MIN_POLL_INTERVAL_SECONDS", "3")

from app.main import app  # noqa: E402
from app.platform.security.operator_api_key import require_operator_api_key  # noqa: E402


async def allow_operator_api_key_for_tests() -> None:
    """Bypass operator auth for tests that do not cover auth behavior.

    Returns:
        None.
    """
    return None


app.dependency_overrides[require_operator_api_key] = allow_operator_api_key_for_tests
