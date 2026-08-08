"""Remove legacy default MINIO smoke provider.

Revision ID: 202605150930_remove_default_minio_smoke_provider
Revises: 202605141904_add_context_vault
Create Date: 2026-05-15 09:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "202605150930_remove_default_minio_smoke_provider"
down_revision: str | None = "202605141904_add_context_vault"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _legacy_default_minio_provider_ids() -> str:
    """Build a dialect-correct legacy provider selector."""
    is_sqlite = op.get_bind().dialect.name == "sqlite"
    enabled_literal = "0" if is_sqlite else "FALSE"
    config_expression = "config" if is_sqlite else "CAST(config AS TEXT)"
    return f"""
        SELECT id
        FROM librarian_providers
        WHERE name = 'default-minio'
          AND provider_type = 'MINIO'
          AND auth_type = 'API_KEY'
          AND enabled = {enabled_literal}
          AND {config_expression} LIKE '%localhost:9000%'
          AND {config_expression} LIKE '%alexandria-smoke%'
    """


def upgrade() -> None:
    """Delete the legacy local MINIO smoke credential from existing dev DBs."""
    provider_ids = _legacy_default_minio_provider_ids()
    op.execute(
        f"""
        DELETE FROM librarian_provider_secrets
        WHERE provider_id IN ({provider_ids})
        """
    )
    op.execute(
        f"""
        DELETE FROM librarian_providers
        WHERE id IN ({provider_ids})
        """
    )


def downgrade() -> None:
    """Do not recreate removed local smoke credentials."""
