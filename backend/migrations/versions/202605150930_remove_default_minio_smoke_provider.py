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

LEGACY_DEFAULT_MINIO_PROVIDER_IDS = """
    SELECT id
    FROM librarian_providers
    WHERE name = 'default-minio'
      AND provider_type = 'MINIO'
      AND auth_type = 'API_KEY'
      AND enabled = 0
      AND config LIKE '%localhost:9000%'
      AND config LIKE '%alexandria-smoke%'
"""


def upgrade() -> None:
    """Delete the legacy local MINIO smoke credential from existing dev DBs."""
    op.execute(
        f"""
        DELETE FROM librarian_provider_secrets
        WHERE provider_id IN ({LEGACY_DEFAULT_MINIO_PROVIDER_IDS})
        """
    )
    op.execute(
        f"""
        DELETE FROM librarian_providers
        WHERE id IN ({LEGACY_DEFAULT_MINIO_PROVIDER_IDS})
        """
    )


def downgrade() -> None:
    """Do not recreate removed local smoke credentials."""
