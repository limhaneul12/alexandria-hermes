"""Add Context Vault storage and retrieval tables.

Revision ID: 202605141904_add_context_vault
Revises: 202605121240_initial_uuid_archive
Create Date: 2026-05-14 19:04:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605141904_add_context_vault"
down_revision: str | None = "202605121240_initial_uuid_archive"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONTEXT_KINDS = (
    "HANDOFF",
    "DECISION",
    "BUG_ROOT_CAUSE",
    "PLAN",
    "COMPACT",
    "RESEARCH",
    "USAGE",
    "MEMORY",
)
CONTENT_FORMATS = ("MARKDOWN", "TEXT")
SOURCE_TYPES = ("AGENT", "USER", "SYSTEM", "IMPORTED")
IMPORTANCE = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
STATUSES = (
    "SAVED",
    "SAVED_WITH_WARNINGS",
    "REDACTED_AND_SAVED",
    "BLOCKED_SECRET_RISK",
    "PENDING_REVIEW",
)


def _in_constraint(values: tuple[str, ...]) -> str:
    return ",".join(f"'{value}'" for value in values)


def upgrade() -> None:
    """Create additive Context Vault tables."""
    op.create_table(
        "contexts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_format", sa.String(length=24), nullable=False),
        sa.Column("project", sa.String(length=255), nullable=True),
        sa.Column("source_agent", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("importance", sa.String(length=16), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("quality_score", sa.Integer(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("restore_prompt", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_count", sa.Integer(), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            f"kind IN ({_in_constraint(CONTEXT_KINDS)})",
            name="ck_contexts_kind",
        ),
        sa.CheckConstraint(
            f"content_format IN ({_in_constraint(CONTENT_FORMATS)})",
            name="ck_contexts_content_format",
        ),
        sa.CheckConstraint(
            f"source_type IN ({_in_constraint(SOURCE_TYPES)})",
            name="ck_contexts_source_type",
        ),
        sa.CheckConstraint(
            f"importance IN ({_in_constraint(IMPORTANCE)})",
            name="ck_contexts_importance",
        ),
        sa.CheckConstraint(
            f"status IN ({_in_constraint(STATUSES)})",
            name="ck_contexts_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_contexts_kind"), "contexts", ["kind"], unique=False)
    op.create_index(op.f("ix_contexts_project"), "contexts", ["project"], unique=False)
    op.create_index(
        op.f("ix_contexts_source_agent"), "contexts", ["source_agent"], unique=False
    )

    op.create_table(
        "context_chunks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("context_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("heading", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["context_id"], ["contexts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_context_chunks_context_id"),
        "context_chunks",
        ["context_id"],
        unique=False,
    )

    op.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS context_chunk_fts USING fts5(
            chunk_id UNINDEXED,
            context_id UNINDEXED,
            title,
            summary,
            content,
            kind,
            project,
            source_agent,
            tags,
            heading,
            tokenize='porter'
        )
        """
    )


def downgrade() -> None:
    """Drop Context Vault tables."""
    op.execute("DROP TABLE IF EXISTS context_chunk_fts")
    op.drop_index(op.f("ix_context_chunks_context_id"), table_name="context_chunks")
    op.drop_table("context_chunks")
    op.drop_index(op.f("ix_contexts_source_agent"), table_name="contexts")
    op.drop_index(op.f("ix_contexts_project"), table_name="contexts")
    op.drop_index(op.f("ix_contexts_kind"), table_name="contexts")
    op.drop_table("contexts")
