"""Add context chunk embedding storage for vector retrieval."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605162010"
down_revision: str | Sequence[str] | None = "202605161945"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable embedding metadata columns to context chunks."""
    op.add_column("context_chunks", sa.Column("embedding", sa.Text(), nullable=True))
    op.add_column(
        "context_chunks",
        sa.Column("embedding_model", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "context_chunks", sa.Column("embedding_dimensions", sa.Integer(), nullable=True)
    )
    op.create_index(
        op.f("ix_context_chunks_embedding_model_dimensions"),
        "context_chunks",
        ["embedding_model", "embedding_dimensions"],
        unique=False,
    )


def downgrade() -> None:
    """Remove context chunk embedding metadata columns."""
    op.drop_index(
        op.f("ix_context_chunks_embedding_model_dimensions"),
        table_name="context_chunks",
    )
    op.drop_column("context_chunks", "embedding_dimensions")
    op.drop_column("context_chunks", "embedding_model")
    op.drop_column("context_chunks", "embedding")
