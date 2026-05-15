"""Add librarian agent profile configuration fields."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605161020"
down_revision: str | Sequence[str] | None = (
    "202605151438_allow_prompt_library_item_type"
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add model, concurrency, and role prompt fields for librarian profiles."""
    op.add_column(
        "agent_profiles",
        sa.Column("preferred_librarian_model", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "agent_profiles",
        sa.Column(
            "max_librarian_agents",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column(
        "agent_profiles",
        sa.Column("librarian_role_prompt", sa.String(length=4096), nullable=True),
    )


def downgrade() -> None:
    """Remove librarian profile configuration fields."""
    op.drop_column("agent_profiles", "librarian_role_prompt")
    op.drop_column("agent_profiles", "max_librarian_agents")
    op.drop_column("agent_profiles", "preferred_librarian_model")
