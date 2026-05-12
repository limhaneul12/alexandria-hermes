"""Helpers for parsing logging record extra fields."""

from __future__ import annotations

import logging


def log_record_extra_str(
    *,
    record: logging.LogRecord,
    key: str,
    default: str | None = None,
) -> str | None:
    """Read an extra field as string with type validation.

    Args:
        record: Python logging record.
        key: Name of the extra field.
        default: Value returned when the field is missing or not a string.

    Return:
        Extra string value, or fallback default.
    """
    value = record.__dict__.get(key)
    if isinstance(value, str):
        return value
    return default


def log_record_extra_str_or_default(
    *,
    record: logging.LogRecord,
    key: str,
    default: str,
) -> str:
    """Read an extra string field and return a required fallback default.

    Args:
        record: See function signature.
        key: See function signature.
        default: See function signature.

    Return:
        Return value.
    """
    value = log_record_extra_str(record=record, key=key, default=default)
    if value is None:
        return default
    return value


def log_record_extra_float(
    *,
    record: logging.LogRecord,
    key: str,
    default: float | None = None,
) -> float | None:
    """Read an extra numeric field as ``float``.

    Args:
        record: Python logging record.
        key: Name of the extra field.
        default: Value returned when the field is missing or non-numeric.

    Return:
        Float-converted value, or fallback default.
    """
    value = record.__dict__.get(key)
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return default


def log_record_extra_int(
    *,
    record: logging.LogRecord,
    key: str,
    default: int | None = None,
) -> int | None:
    """Read an extra integer field safely.

    Args:
        record: Python logging record.
        key: Name of the extra field.
        default: Value returned when the field is missing or not an int.

    Return:
        Integer extra value, or fallback default.
    """
    value = record.__dict__.get(key)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return default
