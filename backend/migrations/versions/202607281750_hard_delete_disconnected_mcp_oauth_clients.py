"""Hard-delete MCP OAuth clients left by legacy soft disconnect.

Revision ID: 202607281750
Revises: 9e4d7b6c2a10
Create Date: 2026-07-28 17:50:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607281750"
down_revision: str | None = "9e4d7b6c2a10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove clients whose refresh tokens were all soft-revoked."""
    connection = op.get_bind()
    client_ids = tuple(
        connection.execute(
            sa.text(
                """
                SELECT client.client_id
                FROM mcp_oauth_clients AS client
                WHERE EXISTS (
                    SELECT 1
                    FROM mcp_oauth_tokens AS token
                    WHERE token.client_id = client.client_id
                      AND token.token_kind = 'refresh'
                )
                  AND NOT EXISTS (
                    SELECT 1
                    FROM mcp_oauth_tokens AS token
                    WHERE token.client_id = client.client_id
                      AND token.token_kind = 'refresh'
                      AND token.revoked_at IS NULL
                )
                """
            )
        ).scalars()
    )
    if not client_ids:
        return

    client_id_parameter = sa.bindparam("client_ids", expanding=True)
    parameters = {"client_ids": client_ids}
    for table_name in (
        "mcp_oauth_authorization_requests",
        "mcp_oauth_authorization_codes",
        "mcp_oauth_tokens",
        "mcp_oauth_clients",
    ):
        connection.execute(
            sa.text(
                f"DELETE FROM {table_name} WHERE client_id IN :client_ids"
            ).bindparams(client_id_parameter),
            parameters,
        )


def downgrade() -> None:
    """Leave irreversible credential deletion in place."""
