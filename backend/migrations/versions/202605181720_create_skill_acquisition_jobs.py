"""Create durable skill acquisition jobs.

Revision ID: 202605181720_create_skill_acquisition_jobs
Revises: 202605181650_add_harness_context_kind
Create Date: 2026-05-18 17:20:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605181720_create_skill_acquisition_jobs"
down_revision: str | None = "202605181650_add_harness_context_kind"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JOB_STATUSES = ("ACCEPTED", "GUIDANCE_ONLY", "COMPLETED", "FAILED")


def _in_constraint(values: tuple[str, ...]) -> str:
    """Return a SQL IN-list for stable enum check constraints.

    Args:
        values: Enum values accepted by the constraint.

    Returns:
        SQL literal list for a CHECK expression.
    """
    return ",".join(f"'{value}'" for value in values)


def upgrade() -> None:
    """Create the durable skill-acquisition job table.

    Returns:
        None.
    """
    op.create_table(
        "skill_acquisition_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("agent_name", sa.String(length=255), nullable=False),
        sa.Column("project", sa.String(length=255), nullable=True),
        sa.Column("task_summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider_id", sa.String(length=36), nullable=True),
        sa.Column("librarian_profile_id", sa.String(length=36), nullable=True),
        sa.Column("skill_id", sa.String(length=36), nullable=True),
        sa.Column("context_id", sa.String(length=36), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("evidence_urls", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            f"status IN ({_in_constraint(JOB_STATUSES)})",
            name="ck_skill_acquisition_jobs_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_skill_acquisition_jobs_project"),
        "skill_acquisition_jobs",
        ["project"],
        unique=False,
    )
    op.create_index(
        op.f("ix_skill_acquisition_jobs_status"),
        "skill_acquisition_jobs",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the durable skill-acquisition job table.

    Returns:
        None.
    """
    op.drop_index(
        op.f("ix_skill_acquisition_jobs_status"), table_name="skill_acquisition_jobs"
    )
    op.drop_index(
        op.f("ix_skill_acquisition_jobs_project"), table_name="skill_acquisition_jobs"
    )
    op.drop_table("skill_acquisition_jobs")
