"""Operator API-key guard behavior tests."""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator

import anyio
from app.main import app
from app.platform.security.operator_api_key import require_operator_api_key
from fastapi import HTTPException
from fastapi.testclient import TestClient

TEST_OPERATOR_API_KEY = "test-operator-api-key-for-route-contracts-000000000000"


@contextmanager
def enforce_operator_api_key_dependency() -> Iterator[None]:
    """Temporarily restore the real operator auth dependency.

    Yields:
        None.
    """
    previous_override = app.dependency_overrides.pop(require_operator_api_key, None)
    try:
        yield
    finally:
        if previous_override is not None:
            app.dependency_overrides[require_operator_api_key] = previous_override


def test_librarian_settings_rejects_missing_operator_key() -> None:
    """Sensitive settings routes should reject unauthenticated requests first."""
    with (
        enforce_operator_api_key_dependency(),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.get("/settings/connections")

    assert response.status_code == 401
    assert response.json() == {"detail": "Operator API key required"}


def test_operator_api_key_accepts_configured_header() -> None:
    """Operator guard should accept the configured header value."""

    async def scenario() -> None:
        await require_operator_api_key(TEST_OPERATOR_API_KEY)

    anyio.run(scenario)


def test_operator_api_key_rejects_wrong_header() -> None:
    """Operator guard should reject mismatched header values."""

    async def scenario() -> None:
        try:
            await require_operator_api_key("wrong-operator-key")
        except HTTPException as exc:
            assert exc.status_code == 401
            assert exc.detail == "Operator API key required"
            return
        raise AssertionError("wrong operator key was accepted")

    anyio.run(scenario)
