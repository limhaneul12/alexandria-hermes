"""Remove legacy workflow library item type.

Revision ID: 202605181430_remove_workflow_library_item_type
Revises: 202605172010_add_context_access_events
Create Date: 2026-05-18 14:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "202605181430_remove_workflow_library_item_type"
down_revision: str | None = "202605172010_add_context_access_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ITEM_TYPES_WITHOUT_WORKFLOW = ("SKILL", "KNOWLEDGE", "PROMPT")
ITEM_TYPES_WITH_WORKFLOW = ("SKILL", "WORKFLOW", "KNOWLEDGE", "PROMPT")


def _in_constraint(values: tuple[str, ...]) -> str:
    """Return a SQL IN-list for stable enum check constraints."""
    return ",".join(f"'{value}'" for value in values)


def _item_type_constraint(values: tuple[str, ...]) -> str:
    """Return the library item type CHECK expression."""
    return f"item_type IN ({_in_constraint(values)})"


def upgrade() -> None:
    """Delete legacy workflow records and remove WORKFLOW from item_type."""
    op.execute(
        """
        DELETE FROM usage_histories
        WHERE item_id IN (
            SELECT id FROM library_items WHERE item_type = 'WORKFLOW'
        )
        """
    )
    op.execute("DELETE FROM library_items WHERE item_type = 'WORKFLOW'")
    with op.batch_alter_table("library_items", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_library_items_type", type_="check")
        batch_op.create_check_constraint(
            "ck_library_items_type",
            _item_type_constraint(ITEM_TYPES_WITHOUT_WORKFLOW),
        )


def downgrade() -> None:
    """Restore the pre-removal item_type constraint without recreating rows."""
    with op.batch_alter_table("library_items", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_library_items_type", type_="check")
        batch_op.create_check_constraint(
            "ck_library_items_type",
            _item_type_constraint(ITEM_TYPES_WITH_WORKFLOW),
        )
