"""Shared OAuth response redaction helpers."""

from __future__ import annotations

from typing import Final

from app.shared.types.extra_types import JSONObject, JSONValue

OAUTH_SENSITIVE_RESPONSE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "access_token",
        "api_key",
        "client_secret",
        "device_code",
        "id_token",
        "oauth_access_token",
        "oauth_device_code",
        "oauth_refresh_token",
        "refresh_token",
        "secret",
        "secrets",
        "token",
        "tokens",
    }
)

OAUTH_DEVICE_USER_INSTRUCTION_KEYS: Final[frozenset[str]] = frozenset(
    {
        "user_code",
        "verification_uri_complete",
    }
)


def _normalized_key(key: str) -> str:
    """Return a punctuation-insensitive key for redaction matching.

    Args:
        key: JSON object key.

    Returns:
        str: Lowercase alphanumeric key.
    """
    return "".join(character for character in key.lower() if character.isalnum())


_OAUTH_SENSITIVE_NORMALIZED_KEYS: Final[frozenset[str]] = frozenset(
    {_normalized_key(key) for key in OAUTH_SENSITIVE_RESPONSE_KEYS}
)
_OAUTH_DEVICE_USER_INSTRUCTION_NORMALIZED_KEYS: Final[frozenset[str]] = frozenset(
    {_normalized_key(key) for key in OAUTH_DEVICE_USER_INSTRUCTION_KEYS}
)


def without_oauth_sensitive_fields(
    payload: JSONValue,
    *,
    keep_device_user_instructions: bool = False,
) -> JSONValue:
    """Remove OAuth credential fields from agent-facing responses.

    Args:
        payload: Backend OAuth lifecycle response.
        keep_device_user_instructions: Whether to keep the device-flow
            ``user_code`` and complete verification URL for a local CLI/UI that
            must show them to the operator.

    Returns:
        JSONValue: Payload without user codes, complete verification URLs, tokens,
            or secrets.
    """
    if isinstance(payload, dict):
        sanitized: JSONObject = {}
        for key, value in payload.items():
            normalized_key = _normalized_key(str(key))
            if normalized_key in _OAUTH_SENSITIVE_NORMALIZED_KEYS:
                continue
            if (
                not keep_device_user_instructions
                and normalized_key in _OAUTH_DEVICE_USER_INSTRUCTION_NORMALIZED_KEYS
            ):
                continue
            sanitized[str(key)] = without_oauth_sensitive_fields(
                value,
                keep_device_user_instructions=keep_device_user_instructions,
            )
        return sanitized
    if isinstance(payload, list):
        return [
            without_oauth_sensitive_fields(
                item,
                keep_device_user_instructions=keep_device_user_instructions,
            )
            for item in payload
        ]
    return payload
