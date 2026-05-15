"""Shared JSON serialization helper module."""

from __future__ import annotations

import json
from typing import cast

from app.shared.types.extra_types import JSONValue

try:
    import orjson  # type: ignore
except ImportError:  # pragma: no cover
    orjson = None


# Broad type justified: orjson default callback can receive unsupported arbitrary objects.
def _json_default(value: object) -> str:
    """Safely convert unsupported JSON values to strings.

    Args:
        value: Unsupported value received from orjson.

    Returns:
        String representation for fallback serialization.
    """
    return str(value)


def dumps_json(value: JSONValue) -> bytes:
    """Serialize a JSON-compatible value with orjson.

    Args:
        value: JSON-compatible value.

    Returns:
        Serialized UTF-8 JSON bytes.
    """
    if orjson is None:  # pragma: no cover
        return json.dumps(value, default=_json_default, ensure_ascii=False).encode(
            "utf-8"
        )

    return orjson.dumps(
        value,
        default=_json_default,
        option=orjson.OPT_UTC_Z,
    )


def dumps_pretty_json(value: JSONValue) -> bytes:
    """Serialize a JSON-compatible value with stable indentation.

    Args:
        value: JSON-compatible value.

    Returns:
        Indented serialized UTF-8 JSON bytes.
    """
    if orjson is None:  # pragma: no cover
        pretty = json.dumps(value, default=_json_default, ensure_ascii=False, indent=2)
        return pretty.encode("utf-8")

    return orjson.dumps(
        value,
        default=_json_default,
        option=orjson.OPT_INDENT_2 | orjson.OPT_UTC_Z,
    )


def loads_json(value: bytes | str) -> JSONValue:
    """Deserialize JSON bytes or text through the shared codec.

    Args:
        value: Serialized JSON bytes or text.

    Returns:
        JSON-compatible decoded value.
    """
    if orjson is None:  # pragma: no cover
        decoded = json.loads(value)
    else:
        decoded = orjson.loads(value)
    json_value = cast(JSONValue, decoded)
    return json_value
