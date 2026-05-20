"""UTCDateTime persistence-boundary contract tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from app.shared.infrastructure.datetime_types import UTCDateTime
from sqlalchemy import Column, MetaData, Table, create_engine, insert, select
from sqlalchemy.exc import StatementError


def test_utc_datetime_restores_sqlite_naive_values_as_utc_aware() -> None:
    """Rows read from SQLite should preserve the backend UTC-aware invariant."""
    engine = create_engine("sqlite:///:memory:", future=True)
    metadata = MetaData()
    events = Table(
        "events",
        metadata,
        Column("observed_at", UTCDateTime(), nullable=False),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(
            insert(events).values(
                observed_at=datetime(
                    2026,
                    5,
                    20,
                    9,
                    30,
                    tzinfo=timezone(timedelta(hours=9)),
                )
            )
        )
        observed_at = connection.execute(select(events.c.observed_at)).scalar_one()

    assert observed_at == datetime(2026, 5, 20, 0, 30, tzinfo=UTC)
    assert observed_at.tzinfo is UTC


def test_utc_datetime_rejects_naive_application_values() -> None:
    """Naive datetimes should not enter persistence from application code."""
    engine = create_engine("sqlite:///:memory:", future=True)
    metadata = MetaData()
    events = Table(
        "events",
        metadata,
        Column("observed_at", UTCDateTime(), nullable=False),
    )
    metadata.create_all(engine)

    with (
        pytest.raises(StatementError, match="timezone-aware"),
        engine.begin() as connection,
    ):
        connection.execute(
            insert(events).values(
                observed_at=datetime(2026, 5, 20, 9, 30),
            )
        )
