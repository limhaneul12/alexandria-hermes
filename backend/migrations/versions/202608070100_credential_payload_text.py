"""Allow encrypted provider credential payloads beyond legacy VARCHAR limits.

Revision ID: 202608070100_credential_text
Revises: 202608062130_pg_search
Create Date: 2026-08-07 01:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202608070100_credential_text"
down_revision: str | None = "202608062130_pg_search"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_CREDENTIAL_VALUE_LENGTH = 2048


def upgrade() -> None:
    """Store encrypted provider credential payloads as unbounded text."""
    with op.batch_alter_table(
        "librarian_provider_secrets",
        recreate="always" if op.get_bind().dialect.name == "sqlite" else "auto",
    ) as batch_op:
        batch_op.alter_column(
            "value",
            existing_type=sa.String(length=LEGACY_CREDENTIAL_VALUE_LENGTH),
            type_=sa.Text(),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Restore the legacy limit only when every stored credential still fits."""
    oversized_count = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT count(*) FROM librarian_provider_secrets "
                "WHERE length(value) > :maximum_length"
            ),
            {"maximum_length": LEGACY_CREDENTIAL_VALUE_LENGTH},
        )
        .scalar_one()
    )
    if int(oversized_count) > 0:
        raise RuntimeError(
            "cannot downgrade librarian_provider_secrets.value while encrypted "
            "credential payloads exceed 2048 characters"
        )
    with op.batch_alter_table(
        "librarian_provider_secrets",
        recreate="always" if op.get_bind().dialect.name == "sqlite" else "auto",
    ) as batch_op:
        batch_op.alter_column(
            "value",
            existing_type=sa.Text(),
            type_=sa.String(length=LEGACY_CREDENTIAL_VALUE_LENGTH),
            existing_nullable=False,
        )
