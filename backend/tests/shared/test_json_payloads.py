"""Shared HTTP JSON payload helper tests."""

from __future__ import annotations

import pytest
from app.shared.utils.http_helpers.json_payloads import (
    decode_json_body,
    extract_json_error_message,
    json_body_bytes,
)


def test_decode_json_body_returns_none_when_body_is_empty() -> None:
    """Empty response bodies should stay representable for 204-style responses."""
    assert decode_json_body(b"") is None


def test_extract_json_error_message_prefers_detail_when_response_is_json() -> None:
    """HTTP JSON error payloads should expose the stable detail field."""
    body = json_body_bytes({"detail": "missing item", "message": "fallback"})

    assert extract_json_error_message(body) == "missing item"


def test_extract_json_error_message_prefers_message_when_detail_is_missing() -> None:
    """HTTP JSON error payloads without detail should expose message."""
    body = json_body_bytes({"message": "invalid request"})

    assert extract_json_error_message(body) == "invalid request"


def test_extract_json_error_message_returns_text_when_body_is_not_json() -> None:
    """Plain-text backend failures should preserve the response evidence."""
    assert extract_json_error_message(b"upstream unavailable") == "upstream unavailable"


def test_decode_json_body_rejects_invalid_json_when_body_is_not_empty() -> None:
    """Invalid non-empty JSON bodies should still surface parser failure."""
    with pytest.raises(ValueError):
        decode_json_body(b"not-json")
