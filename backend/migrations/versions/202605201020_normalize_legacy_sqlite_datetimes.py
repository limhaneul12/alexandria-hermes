"""Normalize legacy SQLite datetimes to explicit UTC.

Revision ID: 202605201020_normalize_legacy_sqlite_datetimes
Revises: 202605192115_remove_knowledge_library_item_type
Create Date: 2026-05-20 10:20:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text
from sqlalchemy.engine import Connection

revision: str = "202605201020_normalize_legacy_sqlite_datetimes"
down_revision: str | None = "202605192115_remove_knowledge_library_item_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UTC_SUFFIX = "+00:00"

SQLITE_UTC_TIMESTAMP_COLUMNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("librarian_providers", ("created_at", "updated_at")),
    ("agent_profiles", ("created_at", "updated_at")),
    ("skill_acquisition_jobs", ("created_at", "updated_at", "completed_at")),
    ("categories", ("created_at", "updated_at")),
    ("library_items", ("created_at", "updated_at")),
    ("usage_histories", ("used_at",)),
    (
        "contexts",
        ("created_at", "updated_at", "last_accessed_at", "expires_at", "archived_at"),
    ),
    ("context_chunks", ("created_at",)),
    ("context_access_events", ("accessed_at",)),
    (
        "memory_compacts",
        ("covered_from", "covered_to", "created_at", "updated_at", "archived_at"),
    ),
)


def upgrade() -> None:
    """Mark legacy SQLite timestamp strings as UTC-aware values.

    SQLite historically stored SQLAlchemy ``DateTime(timezone=True)`` values as
    naive strings, even though the application treats them as UTC. The ORM now
    restores those rows safely through ``UTCDateTime``; this data migration also
    updates the persisted legacy strings so existing rows carry the same UTC
    contract at rest.
    """
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        return

    for table_name, column_names in SQLITE_UTC_TIMESTAMP_COLUMNS:
        for column_name in column_names:
            _append_utc_suffix(bind, table_name, column_name)


def downgrade() -> None:
    """Restore legacy SQLite naive timestamp strings for downgrade symmetry."""
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        return

    for table_name, column_names in SQLITE_UTC_TIMESTAMP_COLUMNS:
        for column_name in column_names:
            _strip_utc_suffix(bind, table_name, column_name)


def _append_utc_suffix(bind: Connection, table_name: str, column_name: str) -> None:
    """Append a UTC offset to non-null SQLite timestamp strings without one."""
    quoted_table = _quote_identifier(table_name)
    quoted_column = _quote_identifier(column_name)
    bind.execute(
        text(
            f"""
            UPDATE {quoted_table}
            SET {quoted_column} = {quoted_column} || '{UTC_SUFFIX}'
            WHERE {quoted_column} IS NOT NULL
              AND {quoted_column} != ''
              AND substr({quoted_column}, -1) != 'Z'
              AND {quoted_column} NOT GLOB '*[+-][0-9][0-9]:[0-9][0-9]'
            """
        )
    )


def _strip_utc_suffix(bind: Connection, table_name: str, column_name: str) -> None:
    """Remove the explicit UTC suffix from SQLite timestamp strings."""
    quoted_table = _quote_identifier(table_name)
    quoted_column = _quote_identifier(column_name)
    bind.execute(
        text(
            f"""
            UPDATE {quoted_table}
            SET {quoted_column} = substr(
                {quoted_column},
                1,
                length({quoted_column}) - length('{UTC_SUFFIX}')
            )
            WHERE {quoted_column} LIKE '%' || '{UTC_SUFFIX}'
            """
        )
    )


def _quote_identifier(identifier: str) -> str:
    """Quote a hard-coded SQLite identifier used by this migration."""
    return '"' + identifier.replace('"', '""') + '"'
