"""Add embedding fingerprint metadata to context and Obsidian chunks.

Revision ID: 202606020050_add_embedding_fingerprints
Revises: 202605281230_add_obsidian_chunk_embeddings
Create Date: 2026-06-02 00:50:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606020050_add_embedding_fingerprints"
down_revision: str | None = "202605281230_add_obsidian_chunk_embeddings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _fingerprint_columns() -> tuple[sa.Column[object], ...]:
    return (
        sa.Column("embedding_provider", sa.String(length=64), nullable=True),
        sa.Column("embedding_provider_version", sa.String(length=128), nullable=True),
        sa.Column("embedding_pooling_mode", sa.String(length=128), nullable=True),
        sa.Column("embedding_normalize", sa.Boolean(), nullable=True),
        sa.Column("embedding_fingerprint_key", sa.String(length=1024), nullable=True),
        sa.Column("embedding_fingerprint", sa.JSON(), nullable=True),
        sa.Column("embedding_indexed_at", sa.DateTime(timezone=True), nullable=True),
    )


def upgrade() -> None:
    """Add nullable embedding fingerprint metadata columns."""
    for table_name in ("context_chunks", "obsidian_chunks"):
        for column in _fingerprint_columns():
            op.add_column(table_name, column)
    op.create_index(
        op.f("ix_context_chunks_embedding_fingerprint_key"),
        "context_chunks",
        ["embedding_fingerprint_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_obsidian_chunks_embedding_fingerprint_key"),
        "obsidian_chunks",
        ["embedding_fingerprint_key"],
        unique=False,
    )


def downgrade() -> None:
    """Remove embedding fingerprint metadata columns."""
    op.drop_index(
        op.f("ix_obsidian_chunks_embedding_fingerprint_key"),
        table_name="obsidian_chunks",
    )
    op.drop_index(
        op.f("ix_context_chunks_embedding_fingerprint_key"),
        table_name="context_chunks",
    )
    for table_name in ("obsidian_chunks", "context_chunks"):
        op.drop_column(table_name, "embedding_indexed_at")
        op.drop_column(table_name, "embedding_fingerprint")
        op.drop_column(table_name, "embedding_fingerprint_key")
        op.drop_column(table_name, "embedding_normalize")
        op.drop_column(table_name, "embedding_pooling_mode")
        op.drop_column(table_name, "embedding_provider_version")
        op.drop_column(table_name, "embedding_provider")
