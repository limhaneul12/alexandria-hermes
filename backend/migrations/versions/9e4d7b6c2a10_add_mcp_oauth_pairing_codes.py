"""add mcp oauth pairing codes.

Revision ID: 9e4d7b6c2a10
Revises: 714900e7251c
Create Date: 2026-07-26 23:40:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9e4d7b6c2a10"
down_revision: str | None = "714900e7251c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create hashed, short-lived MCP pairing-code storage."""
    op.create_table(
        "mcp_oauth_pairing_codes",
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.Integer(), nullable=False),
        sa.Column("consumed_at", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("code_hash"),
    )
    op.create_index(
        "ix_mcp_oauth_pairing_codes_expires_at",
        "mcp_oauth_pairing_codes",
        ["expires_at"],
    )
    op.create_index(
        "ix_mcp_oauth_pairing_codes_consumed_at",
        "mcp_oauth_pairing_codes",
        ["consumed_at"],
    )


def downgrade() -> None:
    """Drop MCP pairing-code storage."""
    op.drop_index(
        "ix_mcp_oauth_pairing_codes_consumed_at",
        table_name="mcp_oauth_pairing_codes",
    )
    op.drop_index(
        "ix_mcp_oauth_pairing_codes_expires_at",
        table_name="mcp_oauth_pairing_codes",
    )
    op.drop_table("mcp_oauth_pairing_codes")
