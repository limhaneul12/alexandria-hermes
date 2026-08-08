"""UTCDateTime persistence-boundary contract tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from app.shared.infrastructure.datetime_types import UTCDateTime
from sqlalchemy.dialects import postgresql


def test_utc_datetime_normalizes_aware_values_to_utc() -> None:
    """PostgreSQL persistence values should preserve the backend UTC-aware invariant."""
    value = datetime(
        2026,
        5,
        20,
        9,
        30,
        tzinfo=timezone(timedelta(hours=9)),
    )
    stored = UTCDateTime().process_bind_param(value, postgresql.dialect())
    restored = UTCDateTime().process_result_value(stored, postgresql.dialect())

    assert stored == datetime(2026, 5, 20, 0, 30, tzinfo=UTC)
    assert restored == datetime(2026, 5, 20, 0, 30, tzinfo=UTC)
    assert restored is not None
    assert restored.tzinfo is UTC


def test_utc_datetime_rejects_naive_application_values() -> None:
    """Naive datetimes should not enter PostgreSQL persistence from application code."""
    with pytest.raises(ValueError, match="timezone-aware"):
        UTCDateTime().process_bind_param(
            datetime(2026, 5, 20, 9, 30),
            postgresql.dialect(),
        )
