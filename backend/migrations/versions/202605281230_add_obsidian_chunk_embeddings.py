"""Add Obsidian chunk embedding storage for Context RAG retrieval.

Revision ID: 202605281230_add_obsidian_chunk_embeddings
Revises: 202605261030_add_obsidian_graph_and_workflows
Create Date: 2026-05-28 12:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605281230_add_obsidian_chunk_embeddings"
down_revision: str | None = "202605261030_add_obsidian_graph_and_workflows"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable embedding metadata columns to Obsidian chunks."""
    op.add_column("obsidian_chunks", sa.Column("embedding", sa.Text(), nullable=True))
    op.add_column(
        "obsidian_chunks",
        sa.Column("embedding_model", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "obsidian_chunks",
        sa.Column("embedding_dimensions", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_obsidian_chunks_embedding_model_dimensions",
        "obsidian_chunks",
        ["embedding_model", "embedding_dimensions"],
        unique=False,
    )


def downgrade() -> None:
    """Remove Obsidian chunk embedding metadata columns."""
    op.drop_index(
        "ix_obsidian_chunks_embedding_model_dimensions",
        table_name="obsidian_chunks",
    )
    op.drop_column("obsidian_chunks", "embedding_dimensions")
    op.drop_column("obsidian_chunks", "embedding_model")
    op.drop_column("obsidian_chunks", "embedding")
