"""JSON output rendering for CLI streams."""

from __future__ import annotations

from typing import TextIO

from app.shared.serialization.orjson_codec import dumps_pretty_json
from app.shared.types.extra_types import JSONValue


def print_json(payload: JSONValue, stdout: TextIO) -> None:
    """Print pretty JSON to the selected stream.

    Args:
        payload: JSON-compatible payload.
        stdout: Destination stream.

    Returns:
        None.
    """
    print(dumps_pretty_json(payload).decode("utf-8"), file=stdout)
