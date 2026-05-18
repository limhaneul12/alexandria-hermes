"""Operator API-key dependency for sensitive backend routes."""

from __future__ import annotations

from hmac import compare_digest
from typing import Annotated, Final

from app.platform.config.app_config import AppConfig
from fastapi import Header, HTTPException, status

OPERATOR_API_KEY_HEADER: Final[str] = "X-Alexandria-Operator-Key"


def configured_operator_api_key(config: AppConfig | None = None) -> str:
    """Return the configured operator API key as plain text for comparison.

    Args:
        config: Optional AppConfig supplied by tests.

    Returns:
        str: Operator API key value.
    """
    app_config = AppConfig() if config is None else config
    return app_config.operator_api_key.get_secret_value()


async def require_operator_api_key(
    operator_api_key: Annotated[
        str | None,
        Header(alias=OPERATOR_API_KEY_HEADER),
    ] = None,
) -> None:
    """Reject requests missing the configured operator API key.

    Args:
        operator_api_key: Request header value for ``X-Alexandria-Operator-Key``.

    Returns:
        None.

    Raises:
        HTTPException: When the request lacks the configured operator key.
    """
    expected_key = configured_operator_api_key()
    if operator_api_key is None or not compare_digest(operator_api_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Operator API key required",
        )
