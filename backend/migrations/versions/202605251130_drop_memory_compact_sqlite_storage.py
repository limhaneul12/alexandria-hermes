"""Drop SQLite Memory Compact storage tables.

Revision ID: 202605251130_drop_memory_compact_sqlite_storage
Revises: 202605251030_drop_library_crud_and_harness_kind
Create Date: 2026-05-25 11:30:00.000000
"""

from __future__ import annotations

from alembic import op

revision: str = "202605251130_drop_memory_compact_sqlite_storage"
down_revision: str | None = "202605251030_drop_library_crud_and_harness_kind"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Remove Memory Compact SQLite tables after moving compacts to Obsidian."""
    op.execute("DROP TABLE IF EXISTS memory_compact_source_refs")
    op.execute("DROP TABLE IF EXISTS memory_compacts")


def downgrade() -> None:
    """Do not recreate deprecated Memory Compact SQLite storage tables."""
