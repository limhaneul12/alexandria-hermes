"""Delete orphaned MCP OAuth state left without a client registration.

Revision ID: 202607281805
Revises: 202607281750
Create Date: 2026-07-28 18:05:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607281805"
down_revision: str | None = "202607281750"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove authorization and token rows whose client no longer exists."""
    connection = op.get_bind()
    for table_name in (
        "mcp_oauth_authorization_requests",
        "mcp_oauth_authorization_codes",
        "mcp_oauth_tokens",
    ):
        connection.execute(
            sa.text(
                f"""
                DELETE FROM {table_name}
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM mcp_oauth_clients AS client
                    WHERE client.client_id = {table_name}.client_id
                )
                """
            )
        )


def downgrade() -> None:
    """Leave irreversible credential deletion in place."""
