"""Add harness context kind.

Revision ID: 202605181650_add_harness_context_kind
Revises: 202605181430_remove_workflow_library_item_type
Create Date: 2026-05-18 16:50:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "202605181650_add_harness_context_kind"
down_revision: str | None = "202605181430_remove_workflow_library_item_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONTEXT_KINDS_WITHOUT_HARNESS = (
    "HANDOFF",
    "DECISION",
    "BUG_ROOT_CAUSE",
    "PLAN",
    "COMPACT",
    "RESEARCH",
    "USAGE",
    "MEMORY",
)
CONTEXT_KINDS_WITH_HARNESS = (*CONTEXT_KINDS_WITHOUT_HARNESS, "HARNESS")


def _in_constraint(values: tuple[str, ...]) -> str:
    """Return a SQL IN-list for stable enum check constraints.

    Args:
        values: Enum values accepted by the constraint.

    Returns:
        SQL literal list for a CHECK expression.
    """
    return ",".join(f"'{value}'" for value in values)


def _context_kind_constraint(values: tuple[str, ...]) -> str:
    """Return the context kind CHECK expression.

    Args:
        values: Context kind values accepted by the constraint.

    Returns:
        SQL CHECK expression for ``contexts.kind``.
    """
    return f"kind IN ({_in_constraint(values)})"


def upgrade() -> None:
    """Allow agent-owned HARNESS context records.

    Returns:
        None.
    """
    with op.batch_alter_table("contexts", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_contexts_kind", type_="check")
        batch_op.create_check_constraint(
            "ck_contexts_kind",
            _context_kind_constraint(CONTEXT_KINDS_WITH_HARNESS),
        )


def downgrade() -> None:
    """Remove HARNESS from the context kind constraint.

    Returns:
        None.
    """
    op.execute("DELETE FROM contexts WHERE kind = 'HARNESS'")
    with op.batch_alter_table("contexts", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_contexts_kind", type_="check")
        batch_op.create_check_constraint(
            "ck_contexts_kind",
            _context_kind_constraint(CONTEXT_KINDS_WITHOUT_HARNESS),
        )
