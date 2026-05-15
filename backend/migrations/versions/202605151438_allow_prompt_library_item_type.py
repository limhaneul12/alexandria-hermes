"""Allow prompt records in library_items.

Revision ID: 202605151438_allow_prompt_library_item_type
Revises: 202605150930_remove_default_minio_smoke_provider
Create Date: 2026-05-15 14:38:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "202605151438_allow_prompt_library_item_type"
down_revision: str | None = "202605150930_remove_default_minio_smoke_provider"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ITEM_TYPES_WITH_PROMPT = ("SKILL", "WORKFLOW", "KNOWLEDGE", "PROMPT")
ITEM_TYPES_WITHOUT_PROMPT = ("SKILL", "WORKFLOW", "KNOWLEDGE")


def _in_constraint(values: tuple[str, ...]) -> str:
    """Return a SQL IN-list for stable enum check constraints."""
    return ",".join(f"'{value}'" for value in values)


def _item_type_constraint(values: tuple[str, ...]) -> str:
    """Return the library item type CHECK expression."""
    return f"item_type IN ({_in_constraint(values)})"


def upgrade() -> None:
    """Expand library_items.item_type so prompt records can be inserted."""
    with op.batch_alter_table("library_items", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_library_items_type", type_="check")
        batch_op.create_check_constraint(
            "ck_library_items_type",
            _item_type_constraint(ITEM_TYPES_WITH_PROMPT),
        )


def downgrade() -> None:
    """Restore the pre-prompt item_type constraint after removing prompt rows."""
    op.execute(
        """
        DELETE FROM usage_histories
        WHERE item_id IN (
            SELECT id FROM library_items WHERE item_type = 'PROMPT'
        )
        """
    )
    op.execute("DELETE FROM library_items WHERE item_type = 'PROMPT'")
    with op.batch_alter_table("library_items", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_library_items_type", type_="check")
        batch_op.create_check_constraint(
            "ck_library_items_type",
            _item_type_constraint(ITEM_TYPES_WITHOUT_PROMPT),
        )
