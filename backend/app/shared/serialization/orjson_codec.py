"""Shared JSON serialization helper module."""

from __future__ import annotations

import json

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
