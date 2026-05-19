"""Helpers for parsing and sanitizing logging record fields."""

from __future__ import annotations

import logging
import re

_SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?P<prefix>[\"']?"
    r"(?:api[_-]?key|oauth[_-]?access[_-]?token|access[_-]?token|"
    r"oauth[_-]?refresh[_-]?token|refresh[_-]?token|"
    r"oauth[_-]?device[_-]?code|device[_-]?code|user[_-]?code|"
    r"password|secret)"
    r"[\"']?\s*[:=]\s*[\"']?)"
    r"(?P<value>[^\"'\s,;}&]+)",
    re.IGNORECASE,
)
_BEARER_TOKEN_RE = re.compile(
    r"(?P<prefix>\bBearer\s+)[A-Za-z0-9._~+/-]+=*",
    re.IGNORECASE,
)


def redact_sensitive_text(value: str | None) -> str | None:
    """Redact likely credential values from log-safe text.

    Args:
        value: Text that may contain key-value formatted credentials.

    Returns:
        Text with credential values replaced by ``<redacted>``.
    """
    if value is None:
        return None
    redacted = _SENSITIVE_ASSIGNMENT_RE.sub(
        lambda match: f"{match.group('prefix')}<redacted>",
        value,
    )
    return _BEARER_TOKEN_RE.sub(
        lambda match: f"{match.group('prefix')}<redacted>",
        redacted,
    )


class LogRecordExtraReader:
    """Typed reader for ``LogRecord.extra`` values from one record."""

    __slots__ = ("_record",)

    def __init__(self, record: logging.LogRecord) -> None:
        """Initialize a typed extra-field reader.

        Args:
            record: Python logging record whose ``extra`` fields are read.
        """
        self._record = record

    def string(self, key: str, *, default: str | None = None) -> str | None:
        """Read an extra field as string with type validation.

        Args:
            key: Name of the extra field.
            default: Value returned when the field is missing or not a string.

        Returns:
            Extra string value, or fallback default.
        """
        value = self._record.__dict__.get(key)
        if isinstance(value, str):
            return value
        return default

    def required_string(self, key: str, *, default: str) -> str:
        """Read an extra string field with a required fallback.

        Args:
            key: Name of the extra field.
            default: Value returned when the field is missing or not a string.

        Returns:
            Extra string value, or required fallback default.
        """
        value = self.string(key, default=default)
        if value is None:
            return default
        return value

    def float_value(
        self,
        key: str,
        *,
        default: float | None = None,
    ) -> float | None:
        """Read an extra numeric field as ``float``.

        Args:
            key: Name of the extra field.
            default: Value returned when the field is missing or non-numeric.

        Returns:
            Float-converted value, or fallback default.
        """
        value = self._record.__dict__.get(key)
        if isinstance(value, int | float) and not isinstance(value, bool):
            return float(value)
        return default

    def int_value(self, key: str, *, default: int | None = None) -> int | None:
        """Read an extra integer field safely.

        Args:
            key: Name of the extra field.
            default: Value returned when the field is missing or not an int.

        Returns:
            Integer extra value, or fallback default.
        """
        value = self._record.__dict__.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        return default
