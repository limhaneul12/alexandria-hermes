"""Tests for shared interface payload conversion helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

import pytest

from app.shared.exceptions import BoundaryValidationError
from app.shared.types.types_convert_utils import (
    optional_iso_utc_datetime,
    bool_value,
    enum_value,
    json_object_value,
    required_datetime_value,
    string_int_items,
    string_items,
    string_value,
)


class ExampleSource(StrEnum):
    """Example string enum for conversion tests."""

    MANUAL = "manual"
    AGENT = "agent"


def test_required_datetime_value_accepts_datetime() -> None:
    """Return the datetime value when the payload value is already typed."""
    value = datetime(2026, 5, 14, tzinfo=UTC)

    converted = required_datetime_value(value, "used_at")

    assert converted is value


def test_optional_iso_utc_datetime_normalizes_string_boundaries() -> None:
    """Return UTC-aware datetimes from optional ISO timestamp strings."""
    zulu_value = optional_iso_utc_datetime("2026-05-14T09:30:00Z")
    naive_value = optional_iso_utc_datetime("2026-05-14T09:30:00")
    offset_value = optional_iso_utc_datetime("2026-05-14T18:30:00+09:00")

    assert zulu_value == datetime(2026, 5, 14, 9, 30, tzinfo=UTC)
    assert naive_value == datetime(2026, 5, 14, 9, 30, tzinfo=UTC)
    assert offset_value == datetime(2026, 5, 14, 9, 30, tzinfo=UTC)


def test_optional_iso_utc_datetime_returns_none_when_absent_or_invalid() -> None:
    """Return None when an optional ISO timestamp is absent or malformed."""
    assert optional_iso_utc_datetime(None) is None
    assert optional_iso_utc_datetime("not-a-date") is None


def test_required_datetime_value_rejects_missing_or_wrong_type() -> None:
    """Raise a validation error when a required datetime is absent or untyped."""
    with pytest.raises(BoundaryValidationError):
        required_datetime_value(None, "used_at")

    with pytest.raises(BoundaryValidationError):
        required_datetime_value("2026-05-14T00:00:00Z", "used_at")


def test_string_items_filters_only_strings() -> None:
    """Return string members from an interface payload list."""
    assert string_items(["alpha", 1, "beta", False]) == ["alpha", "beta"]
    assert string_items("not-list") == []


def test_string_int_items_filters_only_string_and_int_values() -> None:
    """Return string and integer members from an interface payload list."""
    assert string_int_items(["tool", 3, False, 4.2]) == ["tool", 3]
    assert string_int_items({"not": "list"}) == []


def test_json_object_value_returns_dict_or_empty_object() -> None:
    """Return a JSON object only when the payload value is dictionary-shaped."""
    assert json_object_value({"purpose": "test"}) == {"purpose": "test"}
    assert json_object_value(["not", "object"]) == {}


def test_string_and_bool_values_keep_defaults_for_wrong_types() -> None:
    """Return typed scalar defaults when payload values do not match."""
    assert string_value("configured", default="fallback") == "configured"
    assert string_value(42, default="fallback") == "fallback"
    assert bool_value(True, default=False) is True
    assert bool_value("true", default=False) is False


def test_enum_value_accepts_typed_enum_or_enum_string() -> None:
    """Return a typed enum from either enum instances or valid string values."""
    assert (
        enum_value(ExampleSource.MANUAL, ExampleSource, "source")
        is ExampleSource.MANUAL
    )
    assert enum_value("agent", ExampleSource, "source") is ExampleSource.AGENT

    with pytest.raises(BoundaryValidationError):
        enum_value("unknown", ExampleSource, "source")
