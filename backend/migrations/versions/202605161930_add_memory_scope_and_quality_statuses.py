"""Add Context Vault recall scopes and library review statuses.

Revision ID: 202605161930
Revises: 202605161020
Create Date: 2026-05-16 19:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605161930"
down_revision: str | Sequence[str] | None = "202605161020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_ITEM_STATUSES = ("DRAFT", "ACTIVE", "ARCHIVED", "DEPRECATED")
NEW_ITEM_STATUSES = (
    "DRAFT",
    "NEEDS_REVIEW",
    "ACTIVE",
    "ARCHIVED",
    "DEPRECATED",
    "SUPERSEDED",
)
CONTEXT_SCOPES = ("GLOBAL", "PROJECT", "AGENT", "SESSION", "USER")
NEW_CONTEXT_FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS context_chunk_fts USING fts5(
    chunk_id UNINDEXED,
    context_id UNINDEXED,
    title,
    summary,
    content,
    kind,
    project,
    scope,
    workspace_id,
    agent_id,
    user_id,
    session_id,
    source_agent,
    tags,
    heading,
    tokenize='porter'
)
"""
OLD_CONTEXT_FTS_SQL = """
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


def _in_constraint(values: tuple[str, ...]) -> str:
    """Return a SQL IN-list for stable enum check constraints."""
    return ",".join(f"'{value}'" for value in values)


def upgrade() -> None:
    """Add recall scope columns and expand item quality statuses."""
    with op.batch_alter_table("contexts", recreate="always") as batch_op:
        batch_op.add_column(
            sa.Column(
                "scope", sa.String(length=16), nullable=False, server_default="PROJECT"
            )
        )
        batch_op.add_column(
            sa.Column("workspace_id", sa.String(length=512), nullable=True)
        )
        batch_op.add_column(sa.Column("agent_id", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("user_id", sa.String(length=255), nullable=True))
        batch_op.add_column(
            sa.Column("session_id", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "visibility",
                sa.String(length=16),
                nullable=False,
                server_default="PROJECT",
            )
        )
        batch_op.create_check_constraint(
            "ck_contexts_scope",
            f"scope IN ({_in_constraint(CONTEXT_SCOPES)})",
        )
        batch_op.create_check_constraint(
            "ck_contexts_visibility",
            f"visibility IN ({_in_constraint(CONTEXT_SCOPES)})",
        )
    with op.batch_alter_table("library_items", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_library_items_status", type_="check")
        batch_op.create_check_constraint(
            "ck_library_items_status",
            f"status IN ({_in_constraint(NEW_ITEM_STATUSES)})",
        )
    op.execute("DROP TABLE IF EXISTS context_chunk_fts")
    op.execute(NEW_CONTEXT_FTS_SQL)


def downgrade() -> None:
    """Remove recall scope columns and restore older item statuses."""
    op.execute(
        "UPDATE library_items SET status = 'DRAFT' WHERE status = 'NEEDS_REVIEW'"
    )
    op.execute(
        "UPDATE library_items SET status = 'DEPRECATED' WHERE status = 'SUPERSEDED'"
    )
    with op.batch_alter_table("library_items", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_library_items_status", type_="check")
        batch_op.create_check_constraint(
            "ck_library_items_status",
            f"status IN ({_in_constraint(OLD_ITEM_STATUSES)})",
        )
    with op.batch_alter_table("contexts", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_contexts_visibility", type_="check")
        batch_op.drop_constraint("ck_contexts_scope", type_="check")
        batch_op.drop_column("visibility")
        batch_op.drop_column("session_id")
        batch_op.drop_column("user_id")
        batch_op.drop_column("agent_id")
        batch_op.drop_column("workspace_id")
        batch_op.drop_column("scope")
    op.execute("DROP TABLE IF EXISTS context_chunk_fts")
    op.execute(OLD_CONTEXT_FTS_SQL)
