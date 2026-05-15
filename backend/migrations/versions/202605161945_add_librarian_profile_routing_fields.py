"""Add librarian profile routing fields."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605161945"
down_revision: str | Sequence[str] | None = "202605161930"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add deterministic routing metadata to librarian profiles."""
    op.add_column(
        "agent_profiles",
        sa.Column(
            "librarian_role",
            sa.String(length=64),
            nullable=False,
            server_default="DEFAULT_SEARCH",
        ),
    )
    op.add_column(
        "agent_profiles",
        sa.Column(
            "librarian_specialties",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "agent_profiles",
        sa.Column(
            "librarian_routing_priority",
            sa.Integer(),
            nullable=False,
            server_default="100",
        ),
    )
    op.add_column(
        "agent_profiles",
        sa.Column(
            "librarian_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    """Remove deterministic routing metadata from librarian profiles."""
    op.drop_column("agent_profiles", "librarian_enabled")
    op.drop_column("agent_profiles", "librarian_routing_priority")
    op.drop_column("agent_profiles", "librarian_specialties")
    op.drop_column("agent_profiles", "librarian_role")
