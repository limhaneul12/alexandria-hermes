"""SQLAlchemy datetime types with backend-wide UTC invariants."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator[datetime]):
    """Persist and restore datetimes as timezone-aware UTC values.

    SQLite drops timezone metadata even when SQLAlchemy columns use
    ``DateTime(timezone=True)``. This type keeps the invariant at the
    persistence boundary: application code must bind aware datetimes, and values
    read back from the database are restored as UTC-aware datetimes.
    """

    impl = DateTime
    cache_ok = True

    def __init__(self) -> None:
        """Initialize the type with timezone-aware SQLAlchemy storage metadata."""
        super().__init__(timezone=True)

    def process_bind_param(
        self,
        value: datetime | None,
        dialect: Dialect,
    ) -> datetime | None:
        """Normalize outbound values and reject naive application datetimes.

        Args:
            value: Application datetime value being bound to SQL.
            dialect: SQLAlchemy dialect executing the bind.

        Returns:
            UTC-aware datetime for storage, or None for nullable columns.
        """
        del dialect
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("UTCDateTime requires a timezone-aware datetime")
        return value.astimezone(UTC)

    def process_result_value(
        self,
        value: datetime | None,
        dialect: Dialect,
    ) -> datetime | None:
        """Restore inbound database values as UTC-aware datetimes.

        Args:
            value: Datetime value read from the database driver.
            dialect: SQLAlchemy dialect that returned the value.

        Returns:
            UTC-aware datetime, or None for nullable columns.
        """
        del dialect
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
