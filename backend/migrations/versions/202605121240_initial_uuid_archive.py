"""Initial backend-owned archive schema with UUID identifiers.

Revision ID: 202605121240_initial_uuid_archive
Revises:
Create Date: 2026-05-12 12:40:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605121240_initial_uuid_archive"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ITEM_TYPES = ("SKILL", "WORKFLOW", "KNOWLEDGE")
ITEM_STATUSES = ("DRAFT", "ACTIVE", "ARCHIVED", "DEPRECATED")
SOURCE_TYPES = ("USER_CREATED", "AGENT_SUBMITTED", "LIBRARIAN_CREATED", "IMPORTED")
CREATED_BY_TYPES = ("USER", "AGENT", "LIBRARIAN")


def _in_constraint(values: tuple[str, ...]) -> str:
    return ",".join(f"'{value}'" for value in values)


def upgrade() -> None:
    """Create backend archive tables and the SQLite FTS table."""
    op.create_table(
        "categories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("parent_id", sa.String(length=36), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_categories_id"), "categories", ["id"], unique=False)
    op.create_index(
        op.f("ix_categories_parent_id"), "categories", ["parent_id"], unique=False
    )

    op.create_table(
        "agent_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=True),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("preferred_librarian_provider", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "librarian_providers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("provider_type", sa.String(length=20), nullable=False),
        sa.Column("auth_type", sa.String(length=20), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "library_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("item_type", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("category_id", sa.String(length=36), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("created_by_type", sa.String(length=20), nullable=False),
        sa.Column("created_by_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            f"item_type IN ({_in_constraint(ITEM_TYPES)})",
            name="ck_library_items_type",
        ),
        sa.CheckConstraint(
            f"status IN ({_in_constraint(ITEM_STATUSES)})",
            name="ck_library_items_status",
        ),
        sa.CheckConstraint(
            f"source_type IN ({_in_constraint(SOURCE_TYPES)})",
            name="ck_library_items_source_type",
        ),
        sa.CheckConstraint(
            f"created_by_type IN ({_in_constraint(CREATED_BY_TYPES)})",
            name="ck_library_items_created_by_type",
        ),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_library_items_category_id"),
        "library_items",
        ["category_id"],
        unique=False,
    )

    op.create_table(
        "librarian_provider_secrets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider_id", sa.String(length=36), nullable=False),
        sa.Column("key_name", sa.String(length=255), nullable=False),
        sa.Column("value", sa.String(length=2048), nullable=False),
        sa.ForeignKeyConstraint(
            ["provider_id"], ["librarian_providers.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_librarian_provider_secrets_provider_id"),
        "librarian_provider_secrets",
        ["provider_id"],
        unique=False,
    )

    op.create_table(
        "usage_histories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("item_id", sa.String(length=36), nullable=False),
        sa.Column("item_type", sa.String(length=20), nullable=False),
        sa.Column("agent_name", sa.String(length=255), nullable=False),
        sa.Column("librarian_provider", sa.String(length=255), nullable=True),
        sa.Column("query", sa.Text(), nullable=True),
        sa.Column("selection_source", sa.String(length=24), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("feedback", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["item_id"], ["library_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_usage_histories_item_id"),
        "usage_histories",
        ["item_id"],
        unique=False,
    )

    op.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS item_search_fts USING fts5(
            item_id UNINDEXED,
            item_type,
            title,
            summary,
            content,
            tags,
            details,
            tokenize='porter'
        )
        """
    )


def downgrade() -> None:
    """Drop backend archive tables."""
    op.execute("DROP TABLE IF EXISTS item_search_fts")
    op.drop_index(op.f("ix_usage_histories_item_id"), table_name="usage_histories")
    op.drop_table("usage_histories")
    op.drop_index(
        op.f("ix_librarian_provider_secrets_provider_id"),
        table_name="librarian_provider_secrets",
    )
    op.drop_table("librarian_provider_secrets")
    op.drop_index(op.f("ix_library_items_category_id"), table_name="library_items")
    op.drop_table("library_items")
    op.drop_table("librarian_providers")
    op.drop_table("agent_profiles")
    op.drop_index(op.f("ix_categories_parent_id"), table_name="categories")
    op.drop_index(op.f("ix_categories_id"), table_name="categories")
    op.drop_table("categories")
