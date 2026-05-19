"""JSON payload serialization for CLI transport boundaries."""

from __future__ import annotations

from typing import cast

from app.shared.serialization.orjson_codec import dumps_json, loads_json
from app.shared.types.extra_types import JSONObject, JSONValue
from pydantic import BaseModel


def json_bytes(payload: JSONValue) -> bytes:
    """Encode a JSON-compatible payload for HTTP transport.

    Args:
        payload: JSON-compatible payload.

    Returns:
        Serialized UTF-8 JSON bytes.
    """
    encoded = dumps_json(payload)
    return encoded


def decode_json(body: bytes) -> JSONValue:
    """Decode backend JSON response bytes.

    Args:
        body: Response body bytes.

    Returns:
        Decoded JSON-compatible value.
    """
    if not body:
        return None
    decoded = loads_json(body)
    return decoded


def error_message(body: bytes) -> str:
    """Extract a stable CLI error message from response bytes.

    Args:
        body: Response body bytes.

    Returns:
        Error detail or a generic message.
    """
    try:
        payload = decode_json(body)
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


def schema_payload(
    schema: BaseModel,
    *,
    by_alias: bool = False,
    exclude_none: bool = False,
) -> JSONObject:
    """Serialize one Pydantic schema to a JSON object.

    Args:
        schema: Pydantic schema to serialize at a CLI boundary.
        by_alias: Whether serialized field aliases should be used.
        exclude_none: Whether nullable fields with ``None`` values are omitted.

    Returns:
        JSON-compatible object payload.
    """
    payload = cast(
        JSONObject,
        schema.model_dump(mode="json", by_alias=by_alias, exclude_none=exclude_none),
    )
    return payload
