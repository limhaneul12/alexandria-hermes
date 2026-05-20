"""JSON request/response payload helpers for HTTP transport boundaries."""

from __future__ import annotations

from app.shared.serialization.orjson_codec import dumps_json, loads_json
from app.shared.types.extra_types import JSONValue


def json_body_bytes(payload: JSONValue) -> bytes:
    """Encode a JSON-compatible payload for HTTP transport.

    Args:
        payload: JSON-compatible request payload.

    Returns:
        Serialized UTF-8 JSON bytes.
    """
    encoded = dumps_json(payload)
    return encoded


def decode_json_body(body: bytes) -> JSONValue:
    """Decode backend JSON response bytes.

    Args:
        body: Response body bytes.

    Returns:
        Decoded JSON-compatible value, or None for an empty body.
    """
    if not body:
        return None
    decoded = loads_json(body)
    return decoded


def extract_json_error_message(body: bytes) -> str:
    """Extract a stable error message from HTTP response bytes.

    Args:
        body: Response body bytes.

    Returns:
        Error detail/message text, decoded text body, or a generic message.
    """
    try:
        payload = decode_json_body(body)
    except ValueError:
        decoded_body = body.decode("utf-8", errors="replace")
        message = "request failed" if decoded_body == "" else decoded_body
        return message
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if detail is None:
            detail = payload.get("message")
        if isinstance(detail, str):
            return detail
    return "request failed"
