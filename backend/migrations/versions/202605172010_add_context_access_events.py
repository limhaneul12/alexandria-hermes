"""Add Context Vault access event history.

Revision ID: 202605172010_add_context_access_events
Revises: 202605171845_add_memory_compacts
Create Date: 2026-05-17 20:10:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605172010_add_context_access_events"
down_revision: str | None = "202605171845_add_memory_compacts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACTOR_TYPES = ("UI", "AGENT", "LIBRARIAN", "SYSTEM")
ACCESS_METHODS = ("DETAIL_VIEW", "RECALL", "RAG_SEARCH", "MCP_TOOL")


def _in_constraint(values: tuple[str, ...]) -> str:
    return ",".join(f"'{value}'" for value in values)


def upgrade() -> None:
    """Create Context Vault access event table."""
    op.create_table(
        "context_access_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("context_id", sa.String(length=36), nullable=False),
        sa.Column("accessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_name", sa.String(length=255), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("access_method", sa.String(length=32), nullable=False),
        sa.Column("source_surface", sa.String(length=255), nullable=True),
        sa.CheckConstraint(
            f"actor_type IN ({_in_constraint(ACTOR_TYPES)})",
            name="ck_context_access_events_actor_type",
        ),
        sa.CheckConstraint(
            f"access_method IN ({_in_constraint(ACCESS_METHODS)})",
            name="ck_context_access_events_access_method",
        ),
        sa.ForeignKeyConstraint(["context_id"], ["contexts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_context_access_events_context_id"),
        "context_access_events",
        ["context_id"],
    )
    op.create_index(
        op.f("ix_context_access_events_accessed_at"),
        "context_access_events",
        ["accessed_at"],
    )


def downgrade() -> None:
    """Drop Context Vault access event table."""
    op.drop_index(
        op.f("ix_context_access_events_accessed_at"),
        table_name="context_access_events",
    )
    op.drop_index(
        op.f("ix_context_access_events_context_id"),
        table_name="context_access_events",
    )
    op.drop_table("context_access_events")
