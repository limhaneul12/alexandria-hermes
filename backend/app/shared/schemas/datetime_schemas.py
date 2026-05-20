"""Shared datetime schema contracts."""

from __future__ import annotations

from typing import Annotated

from app.shared.types.extra_types import JSONValue
from pydantic import AwareDatetime, BeforeValidator


def _reject_numeric_datetime(value: JSONValue) -> JSONValue:
    """Reject epoch-style timestamps at public schema boundaries.

    Args:
        value: Raw value received by Pydantic before datetime parsing.

    Returns:
        Original value when it is not a numeric timestamp.

    Raises:
        ValueError: When the value is numeric.
    """
    if isinstance(value, int | float):
        raise ValueError("datetime value must be an ISO-8601 string")
    return value


type AwareTimestamp = Annotated[
    AwareDatetime,
    BeforeValidator(_reject_numeric_datetime),
]
