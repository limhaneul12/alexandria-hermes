"""Hard-delete helpers for Context Vault persistence."""

from __future__ import annotations

from app.memory.infrastructure.models.context_models import (
    ContextAccessEventORM,
    ContextChunkORM,
    ContextORM,
)
from app.memory.infrastructure.repositories.contexts.fts_sync import remove_context_fts
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession


async def delete_context_rows(
    *, session: AsyncSession, context_id: str, model: ContextORM
) -> None:
    """Delete one context and dependent retrieval/audit rows.

    Args:
        session: Active async session.
        context_id: Context identifier.
        model: Loaded context ORM row.

    Returns:
        None.
    """
    await remove_context_fts(session=session, context_id=context_id)
    await session.execute(
        delete(ContextAccessEventORM).where(
            ContextAccessEventORM.context_id == context_id
        )
    )
    await session.execute(
        delete(ContextChunkORM).where(ContextChunkORM.context_id == context_id)
    )
    await session.delete(model)
    await session.flush()
