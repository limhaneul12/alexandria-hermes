"""Add PostgreSQL vector and lexical search storage.

Revision ID: 202608062130_pg_search
Revises: 202607281805
Create Date: 2026-08-06 21:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "202608062130_pg_search"
down_revision: str | None = "202607281805"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VECTOR_DIMENSIONS = 384

POSTGRES_LEXICAL_INDEXES = (
    (
        "ix_context_chunks_search_document",
        "context_chunks",
        "to_tsvector('simple', coalesce(heading, '') || ' ' || content)",
    ),
    (
        "ix_contexts_search_document",
        "contexts",
        "to_tsvector('simple', title || ' ' || summary || ' ' || content || ' ' || "
        "coalesce(project, '') || ' ' || source_agent)",
    ),
    (
        "ix_obsidian_chunks_search_document",
        "obsidian_chunks",
        "to_tsvector('simple', coalesce(heading_path, '') || ' ' || text)",
    ),
    (
        "ix_obsidian_files_search_document",
        "obsidian_files",
        "to_tsvector('simple', title || ' ' || body || ' ' || "
        "coalesce(project, '') || ' ' || relative_path)",
    ),
)


def upgrade() -> None:
    """Enable pgvector and convert rebuildable embedding/search columns."""
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    for table_name in ("context_chunks", "obsidian_chunks"):
        op.execute(
            f"""
            ALTER TABLE {table_name}
            ALTER COLUMN embedding TYPE vector({VECTOR_DIMENSIONS})
            USING CASE
                WHEN embedding IS NULL OR btrim(embedding) = '' THEN NULL
                ELSE embedding::vector
            END
            """
        )
    for index_name, table_name, expression in POSTGRES_LEXICAL_INDEXES:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {index_name} "
            f"ON {table_name} USING gin ({expression})"
        )


def downgrade() -> None:
    """Restore text embedding columns while leaving shared extensions installed."""
    if op.get_bind().dialect.name != "postgresql":
        return
    for index_name, _, _ in reversed(POSTGRES_LEXICAL_INDEXES):
        op.execute(f"DROP INDEX IF EXISTS {index_name}")
    for table_name in ("context_chunks", "obsidian_chunks"):
        op.execute(
            f"""
            ALTER TABLE {table_name}
            ALTER COLUMN embedding TYPE TEXT
            USING embedding::text
            """
        )
