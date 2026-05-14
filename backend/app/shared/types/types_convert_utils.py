"""Shared conversion helpers for interface payload values."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from app.shared.exceptions import ValidationError
from app.shared.types.extra_types import JSONObject, JSONValue


def now_utc() -> datetime:
    """Return the current UTC timestamp.

    Returns:
        datetime: Timezone-aware current timestamp in UTC.
    """
    return datetime.now(UTC)


def required_datetime_value(value: JSONValue | None, field_name: str) -> datetime:
    """Return a required datetime from an interface payload value.

    Args:
        value: Interface payload value to validate.
        field_name: Field name used in validation errors.

    Returns:
        datetime: Validated datetime value.

    Raises:
        ValidationError: When the value is not a datetime.
    """
    if isinstance(value, datetime):
        return value
    raise ValidationError(f"{field_name} must be a datetime")


def required_string_value(value: JSONValue | None, field_name: str) -> str:
    """Return a required string from an interface payload value.

    Args:
        value: Interface payload value to validate.
        field_name: Field name used in validation errors.

    Returns:
        str: Validated string value.

    Raises:
        ValidationError: When the value is not a string.
    """
    if isinstance(value, str):
        return value
    raise ValidationError(f"{field_name} must be a string")


def optional_string_value(value: JSONValue | None) -> str | None:
    """Return an optional string from an interface payload value.

    Args:
        value: Interface payload value to narrow.

    Returns:
        str | None: String value when present and typed, otherwise ``None``.
    """
    if isinstance(value, str):
        return value
    return None


def string_value(value: JSONValue | None, *, default: str = "") -> str:
    """Return a string value or a caller-provided default.

    Args:
        value: Interface payload value to narrow.
        default: Fallback string for missing or mistyped values.

    Returns:
        str: String value or fallback default.
    """
    if isinstance(value, str):
        return value
    return default


def bool_value(value: JSONValue | None, *, default: bool = False) -> bool:
    """Return a boolean value or a caller-provided default.

    Args:
        value: Interface payload value to narrow.
        default: Fallback boolean for missing or mistyped values.

    Returns:
        bool: Boolean value or fallback default.
    """
    if isinstance(value, bool):
        return value
    return default


def json_object_value(value: JSONValue | None) -> JSONObject:
    """Return a JSON object from an interface payload value.

    Args:
        value: Interface payload value to narrow.

    Returns:
        JSONObject: Dictionary payload when typed, otherwise an empty object.
    """
    if isinstance(value, dict):
        return value
    return {}


def string_items(value: JSONValue | None) -> list[str]:
    """Return string items from an interface payload list.

    Args:
        value: Interface payload value expected to hold a list.

    Returns:
        list[str]: String members only, or an empty list for non-list values.
    """
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def string_int_items(value: JSONValue | None) -> list[str | int]:
    """Return string and integer items from an interface payload list.

    Args:
        value: Interface payload value expected to hold a list.

    Returns:
        list[str | int]: String and non-boolean integer members only.
    """
    if not isinstance(value, list):
        return []
    return [
        item
        for item in value
        if isinstance(item, str)
        or (isinstance(item, int) and not isinstance(item, bool))
    ]


def enum_value[EnumValue: StrEnum](
    value: JSONValue | EnumValue | None,
    enum_type: type[EnumValue],
    field_name: str,
) -> EnumValue:
    """Return a typed string enum from an interface payload value.

    Args:
        value: Interface payload value to validate.
        enum_type: Target ``StrEnum`` subclass.
        field_name: Field name used in validation errors.

    Returns:
        EnumValue: Enum instance matching the input value.

    Raises:
        ValidationError: When the value is not a valid enum string.
    """
    if isinstance(value, enum_type):
        return value
    if isinstance(value, str):
        try:
            return enum_type(value)
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be a valid string") from exc
    raise ValidationError(f"{field_name} must be a valid string")
