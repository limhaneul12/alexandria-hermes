"""Remove legacy MINIO providers.

Revision ID: 202605191840_remove_minio_providers
Revises: 202605181720_create_skill_acquisition_jobs
Create Date: 2026-05-19 18:40:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605191840_remove_minio_providers"
down_revision: str | None = "202605181720_create_skill_acquisition_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Delete object-storage providers now removed from the core product.

    Returns:
        None.
    """
    op.execute(
        sa.text(
            """
            DELETE FROM librarian_provider_secrets
            WHERE provider_id IN (
                SELECT id FROM librarian_providers WHERE provider_type = 'MINIO'
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM librarian_providers
            WHERE provider_type = 'MINIO'
            """
        )
    )


def downgrade() -> None:
    """Keep removed MINIO providers deleted on downgrade.

    Returns:
        None.
    """
