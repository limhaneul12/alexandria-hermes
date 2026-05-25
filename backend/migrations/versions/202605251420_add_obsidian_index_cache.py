"""Add Obsidian Markdown index cache tables.

Revision ID: 202605251420_add_obsidian_index_cache
Revises: 202605251130_drop_memory_compact_sqlite_storage
Create Date: 2026-05-25 14:20:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605251420_add_obsidian_index_cache"
down_revision: str | None = "202605251130_drop_memory_compact_sqlite_storage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create rebuildable Obsidian index cache tables."""
    op.create_table(
        "obsidian_files",
        sa.Column("note_id", sa.String(length=255), primary_key=True),
        sa.Column("relative_path", sa.String(length=1024), nullable=False),
        sa.Column("alexandria_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("project", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("frontmatter_json", sa.JSON(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("index_status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("relative_path", name="uq_obsidian_files_path"),
    )
    op.create_index(
        "ix_obsidian_files_relative_path", "obsidian_files", ["relative_path"]
    )
    op.create_index(
        "ix_obsidian_files_alexandria_type", "obsidian_files", ["alexandria_type"]
    )
    op.create_index("ix_obsidian_files_status", "obsidian_files", ["status"])
    op.create_index("ix_obsidian_files_project", "obsidian_files", ["project"])
    op.create_index(
        "ix_obsidian_files_content_hash", "obsidian_files", ["content_hash"]
    )
    op.create_index(
        "ix_obsidian_files_index_status", "obsidian_files", ["index_status"]
    )
    op.create_table(
        "obsidian_chunks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("note_id", sa.String(length=255), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("heading_path", sa.String(length=512), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["note_id"], ["obsidian_files.note_id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_obsidian_chunks_note_id", "obsidian_chunks", ["note_id"])
    op.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS obsidian_chunk_fts USING fts5(
            chunk_id UNINDEXED,
            note_id UNINDEXED,
            title,
            body,
            heading_path,
            alexandria_type,
            project,
            status,
            tags,
            relative_path,
            tokenize='porter'
        )
        """
    )


def downgrade() -> None:
    """Drop rebuildable Obsidian index cache tables."""
    op.execute("DROP TABLE IF EXISTS obsidian_chunk_fts")
    op.drop_index("ix_obsidian_chunks_note_id", table_name="obsidian_chunks")
    op.drop_table("obsidian_chunks")
    op.drop_index("ix_obsidian_files_index_status", table_name="obsidian_files")
    op.drop_index("ix_obsidian_files_content_hash", table_name="obsidian_files")
    op.drop_index("ix_obsidian_files_project", table_name="obsidian_files")
    op.drop_index("ix_obsidian_files_status", table_name="obsidian_files")
    op.drop_index("ix_obsidian_files_alexandria_type", table_name="obsidian_files")
    op.drop_index("ix_obsidian_files_relative_path", table_name="obsidian_files")
    op.drop_table("obsidian_files")
