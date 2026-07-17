"""Add skill-acquisition search audit fields.

Revision ID: 202606021145_add_skill_acquisition_search_audit_fields
Revises: 202606021130_add_skill_acquisition_handoff_fields
Create Date: 2026-06-02 11:45:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606021145_add_skill_acquisition_search_audit_fields"
down_revision: str | None = "202606021130_add_skill_acquisition_handoff_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_SEARCH_AUDIT_COLUMNS: tuple[sa.Column[object], ...] = (
    sa.Column("search_snapshot", sa.JSON(), nullable=True),
    sa.Column("acquisition_override_reason", sa.Text(), nullable=True),
    sa.Column("prompt_reference", sa.String(length=255), nullable=True),
    sa.Column("prompt_reference_hash", sa.String(length=64), nullable=True),
)


def upgrade() -> None:
    """Add nullable search audit fields to durable skill-acquisition jobs."""
    for column in _SEARCH_AUDIT_COLUMNS:
        op.add_column("skill_acquisition_jobs", column)


def downgrade() -> None:
    """Remove skill-acquisition search audit fields."""
    for column_name in (
        "prompt_reference",
        "prompt_reference_hash",
        "acquisition_override_reason",
        "search_snapshot",
    ):
        op.drop_column("skill_acquisition_jobs", column_name)
