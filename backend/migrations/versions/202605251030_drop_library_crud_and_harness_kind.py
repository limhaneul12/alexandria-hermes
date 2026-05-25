"""Drop SQLite library CRUD tables and harness context kind.

Revision ID: 202605251030_drop_library_crud_and_harness_kind
Revises: 202605201030_reject_legacy_provider_secret_storage
Create Date: 2026-05-25 10:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "202605251030_drop_library_crud_and_harness_kind"
down_revision: str | None = "202605201030_reject_legacy_provider_secret_storage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONTEXT_KINDS = (
    "HANDOFF",
    "DECISION",
    "BUG_ROOT_CAUSE",
    "PLAN",
    "COMPACT",
    "RESEARCH",
    "USAGE",
    "MEMORY",
)


def _context_kind_constraint(values: tuple[str, ...]) -> str:
    accepted = ",".join(f"'{value}'" for value in values)
    return f"kind IN ({accepted})"


def upgrade() -> None:
    """Remove backend-owned SQLite CRUD storage for library assets.

    Returns:
        None.
    """
    op.execute("DROP TABLE IF EXISTS item_search_fts")
    op.execute("DROP TABLE IF EXISTS usage_histories")
    op.execute("DROP TABLE IF EXISTS library_items")
    op.execute("DROP TABLE IF EXISTS categories")
    op.execute("DELETE FROM contexts WHERE kind = 'HARNESS'")
    with op.batch_alter_table("contexts", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_contexts_kind", type_="check")
        batch_op.create_check_constraint(
            "ck_contexts_kind",
            _context_kind_constraint(CONTEXT_KINDS),
        )


def downgrade() -> None:
    """This destructive pruning migration is intentionally not reversible.

    Returns:
        None.
    """
    raise RuntimeError(
        "SQLite library CRUD and HARNESS context restoration is intentionally unsupported."
    )
