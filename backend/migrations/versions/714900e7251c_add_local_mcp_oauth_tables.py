"""add local mcp oauth tables.

Revision ID: 714900e7251c
Revises: 38a1eeb8d848
Create Date: 2026-07-25 21:23:03.527024
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "714900e7251c"
down_revision: str | None = "38a1eeb8d848"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create durable local MCP OAuth state tables."""
    op.create_table(
        "mcp_oauth_clients",
        sa.Column("client_id", sa.String(length=128), nullable=False),
        sa.Column("client_secret_ciphertext", sa.Text(), nullable=True),
        sa.Column("client_metadata", sa.JSON(), nullable=False),
        sa.Column("issued_at", sa.Integer(), nullable=False),
        sa.Column("secret_expires_at", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("client_id"),
    )
    op.create_table(
        "mcp_oauth_authorization_requests",
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("client_id", sa.String(length=128), nullable=False),
        sa.Column("client_name", sa.String(length=255), nullable=True),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("code_challenge", sa.String(length=256), nullable=False),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column("redirect_uri_provided_explicitly", sa.Boolean(), nullable=False),
        sa.Column("resource", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.Integer(), nullable=False),
        sa.Column("approval_attempts", sa.Integer(), nullable=False),
        sa.Column("consumed_at", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["mcp_oauth_clients.client_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("request_id"),
    )
    op.create_index(
        "ix_mcp_oauth_authorization_requests_client_id",
        "mcp_oauth_authorization_requests",
        ["client_id"],
    )
    op.create_index(
        "ix_mcp_oauth_authorization_requests_consumed_at",
        "mcp_oauth_authorization_requests",
        ["consumed_at"],
    )
    op.create_index(
        "ix_mcp_oauth_authorization_requests_expires_at",
        "mcp_oauth_authorization_requests",
        ["expires_at"],
    )
    op.create_table(
        "mcp_oauth_authorization_codes",
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.String(length=128), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("code_challenge", sa.String(length=256), nullable=False),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column("redirect_uri_provided_explicitly", sa.Boolean(), nullable=False),
        sa.Column("resource", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.Integer(), nullable=False),
        sa.Column("consumed_at", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["mcp_oauth_clients.client_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("code_hash"),
    )
    op.create_index(
        "ix_mcp_oauth_authorization_codes_client_id",
        "mcp_oauth_authorization_codes",
        ["client_id"],
    )
    op.create_index(
        "ix_mcp_oauth_authorization_codes_consumed_at",
        "mcp_oauth_authorization_codes",
        ["consumed_at"],
    )
    op.create_index(
        "ix_mcp_oauth_authorization_codes_expires_at",
        "mcp_oauth_authorization_codes",
        ["expires_at"],
    )
    op.create_table(
        "mcp_oauth_tokens",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("token_kind", sa.String(length=16), nullable=False),
        sa.Column("family_id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.String(length=128), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("resource", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.Integer(), nullable=False),
        sa.Column("revoked_at", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["mcp_oauth_clients.client_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("token_hash"),
    )
    op.create_index(
        "ix_mcp_oauth_tokens_client_id",
        "mcp_oauth_tokens",
        ["client_id"],
    )
    op.create_index(
        "ix_mcp_oauth_tokens_expires_at",
        "mcp_oauth_tokens",
        ["expires_at"],
    )
    op.create_index(
        "ix_mcp_oauth_tokens_family_id",
        "mcp_oauth_tokens",
        ["family_id"],
    )
    op.create_index(
        "ix_mcp_oauth_tokens_revoked_at",
        "mcp_oauth_tokens",
        ["revoked_at"],
    )
    op.create_index(
        "ix_mcp_oauth_tokens_token_kind",
        "mcp_oauth_tokens",
        ["token_kind"],
    )


def downgrade() -> None:
    """Drop durable local MCP OAuth state tables."""
    op.drop_index("ix_mcp_oauth_tokens_token_kind", table_name="mcp_oauth_tokens")
    op.drop_index("ix_mcp_oauth_tokens_revoked_at", table_name="mcp_oauth_tokens")
    op.drop_index("ix_mcp_oauth_tokens_family_id", table_name="mcp_oauth_tokens")
    op.drop_index("ix_mcp_oauth_tokens_expires_at", table_name="mcp_oauth_tokens")
    op.drop_index("ix_mcp_oauth_tokens_client_id", table_name="mcp_oauth_tokens")
    op.drop_table("mcp_oauth_tokens")
    op.drop_index(
        "ix_mcp_oauth_authorization_codes_expires_at",
        table_name="mcp_oauth_authorization_codes",
    )
    op.drop_index(
        "ix_mcp_oauth_authorization_codes_consumed_at",
        table_name="mcp_oauth_authorization_codes",
    )
    op.drop_index(
        "ix_mcp_oauth_authorization_codes_client_id",
        table_name="mcp_oauth_authorization_codes",
    )
    op.drop_table("mcp_oauth_authorization_codes")
    op.drop_index(
        "ix_mcp_oauth_authorization_requests_expires_at",
        table_name="mcp_oauth_authorization_requests",
    )
    op.drop_index(
        "ix_mcp_oauth_authorization_requests_consumed_at",
        table_name="mcp_oauth_authorization_requests",
    )
    op.drop_index(
        "ix_mcp_oauth_authorization_requests_client_id",
        table_name="mcp_oauth_authorization_requests",
    )
    op.drop_table("mcp_oauth_authorization_requests")
    op.drop_table("mcp_oauth_clients")
