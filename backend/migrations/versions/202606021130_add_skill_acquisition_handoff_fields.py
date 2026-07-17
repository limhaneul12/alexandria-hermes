"""Add skill-acquisition stage and handoff fields.

Revision ID: 202606021130_add_skill_acquisition_handoff_fields
Revises: 202606020050_add_embedding_fingerprints
Create Date: 2026-06-02 11:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606021130_add_skill_acquisition_handoff_fields"
down_revision: str | None = "202606020050_add_embedding_fingerprints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_HANDOFF_COLUMNS: tuple[sa.Column[object], ...] = (
    sa.Column("stage", sa.String(length=64), nullable=True),
    sa.Column("progress_summary", sa.Text(), nullable=True),
    sa.Column("skill_note_path", sa.String(length=1024), nullable=True),
    sa.Column("reindex_status", sa.String(length=64), nullable=True),
    sa.Column("verification_status", sa.String(length=64), nullable=True),
    sa.Column("handoff", sa.JSON(), nullable=True),
    sa.Column("repair_hint", sa.Text(), nullable=True),
)


def upgrade() -> None:
    """Add nullable stage/handoff fields to durable skill-acquisition jobs."""
    for column in _HANDOFF_COLUMNS:
        op.add_column("skill_acquisition_jobs", column)


def downgrade() -> None:
    """Remove skill-acquisition stage/handoff fields."""
    for column_name in (
        "repair_hint",
        "handoff",
        "verification_status",
        "reindex_status",
        "skill_note_path",
        "progress_summary",
        "stage",
    ):
        op.drop_column("skill_acquisition_jobs", column_name)
