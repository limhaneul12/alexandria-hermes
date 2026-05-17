"""Add Memory Compact artifacts.

Revision ID: 202605171845_add_memory_compacts
Revises: 202605162010
Create Date: 2026-05-17 18:45:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605171845_add_memory_compacts"
down_revision: str | None = "202605162010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MEMORY_COMPACT_STATUSES = ("DRAFT", "CURRENT", "SUPERSEDED", "ARCHIVED")


def _in_constraint(values: tuple[str, ...]) -> str:
    return ",".join(f"'{value}'" for value in values)


def upgrade() -> None:
    """Create Memory Compact tables."""
    op.create_table(
        "memory_compacts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project", sa.String(length=255), nullable=True),
        sa.Column("covered_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("covered_to", sa.DateTime(timezone=True), nullable=False),
        sa.Column("markdown_body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            f"status IN ({_in_constraint(MEMORY_COMPACT_STATUSES)})",
            name="ck_memory_compacts_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_memory_compacts_project"), "memory_compacts", ["project"])
    op.create_index(op.f("ix_memory_compacts_status"), "memory_compacts", ["status"])
    op.create_index(
        "uq_memory_compacts_current_project",
        "memory_compacts",
        ["project"],
        unique=True,
        sqlite_where=sa.text("status = 'CURRENT' AND project IS NOT NULL"),
        postgresql_where=sa.text("status = 'CURRENT' AND project IS NOT NULL"),
    )
    op.create_index(
        "uq_memory_compacts_current_default_project",
        "memory_compacts",
        ["status"],
        unique=True,
        sqlite_where=sa.text("status = 'CURRENT' AND project IS NULL"),
        postgresql_where=sa.text("status = 'CURRENT' AND project IS NULL"),
    )
    op.create_table(
        "memory_compact_source_refs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("compact_id", sa.String(length=36), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("detail_path", sa.String(length=512), nullable=False),
        sa.ForeignKeyConstraint(
            ["compact_id"], ["memory_compacts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_memory_compact_source_refs_compact_id"),
        "memory_compact_source_refs",
        ["compact_id"],
    )


def downgrade() -> None:
    """Drop Memory Compact tables."""
    op.drop_index(
        op.f("ix_memory_compact_source_refs_compact_id"),
        table_name="memory_compact_source_refs",
    )
    op.drop_table("memory_compact_source_refs")
    op.drop_index(
        "uq_memory_compacts_current_default_project",
        table_name="memory_compacts",
    )
    op.drop_index("uq_memory_compacts_current_project", table_name="memory_compacts")
    op.drop_index(op.f("ix_memory_compacts_status"), table_name="memory_compacts")
    op.drop_index(op.f("ix_memory_compacts_project"), table_name="memory_compacts")
    op.drop_table("memory_compacts")
