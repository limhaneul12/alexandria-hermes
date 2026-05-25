"""Add Obsidian graph edges and librarian workflow checkpoints.

Revision ID: 202605261030_add_obsidian_graph_and_workflows
Revises: 202605251420_add_obsidian_index_cache
Create Date: 2026-05-26 10:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605261030_add_obsidian_graph_and_workflows"
down_revision: str | None = "202605251420_add_obsidian_index_cache"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create rebuildable graph edge and workflow checkpoint tables."""
    op.create_table(
        "obsidian_edges",
        sa.Column("edge_id", sa.String(length=64), primary_key=True),
        sa.Column("source_note_id", sa.String(length=255), nullable=False),
        sa.Column("source_path", sa.String(length=1024), nullable=False),
        sa.Column("target_note_id", sa.String(length=255), nullable=True),
        sa.Column("target_path", sa.String(length=1024), nullable=False),
        sa.Column("relation", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source_kind", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_note_id"], ["obsidian_files.note_id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_obsidian_edges_source_note_id", "obsidian_edges", ["source_note_id"]
    )
    op.create_index("ix_obsidian_edges_source_path", "obsidian_edges", ["source_path"])
    op.create_index(
        "ix_obsidian_edges_target_note_id", "obsidian_edges", ["target_note_id"]
    )
    op.create_index("ix_obsidian_edges_target_path", "obsidian_edges", ["target_path"])
    op.create_index("ix_obsidian_edges_relation", "obsidian_edges", ["relation"])
    op.create_index("ix_obsidian_edges_source_kind", "obsidian_edges", ["source_kind"])
    op.create_table(
        "obsidian_librarian_workflows",
        sa.Column("thread_id", sa.String(length=255), primary_key=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("active_note_path", sa.String(length=1024), nullable=True),
        sa.Column("project", sa.String(length=255), nullable=True),
        sa.Column("provider_id", sa.String(length=255), nullable=True),
        sa.Column("profile_id", sa.String(length=255), nullable=True),
        sa.Column("delegate_requested", sa.Boolean(), nullable=False),
        sa.Column("state_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_obsidian_librarian_workflows_status",
        "obsidian_librarian_workflows",
        ["status"],
    )
    op.create_index(
        "ix_obsidian_librarian_workflows_project",
        "obsidian_librarian_workflows",
        ["project"],
    )


def downgrade() -> None:
    """Drop graph edge and workflow checkpoint tables."""
    op.drop_index(
        "ix_obsidian_librarian_workflows_project",
        table_name="obsidian_librarian_workflows",
    )
    op.drop_index(
        "ix_obsidian_librarian_workflows_status",
        table_name="obsidian_librarian_workflows",
    )
    op.drop_table("obsidian_librarian_workflows")
    op.drop_index("ix_obsidian_edges_source_kind", table_name="obsidian_edges")
    op.drop_index("ix_obsidian_edges_relation", table_name="obsidian_edges")
    op.drop_index("ix_obsidian_edges_target_path", table_name="obsidian_edges")
    op.drop_index("ix_obsidian_edges_target_note_id", table_name="obsidian_edges")
    op.drop_index("ix_obsidian_edges_source_path", table_name="obsidian_edges")
    op.drop_index("ix_obsidian_edges_source_note_id", table_name="obsidian_edges")
    op.drop_table("obsidian_edges")
