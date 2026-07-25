"""SQL-backed Context FTS and vector search store."""

from __future__ import annotations

from app.memory.domain.contracts.context_recall_contracts import (
    ContextFtsRecall,
    ContextVectorRecall,
)
from app.memory.domain.entities.context_read_models import ContextSearchMatch
from app.memory.infrastructure.repositories.contexts.fts import (
    ensure_context_chunk_fts_table,
)
from app.memory.infrastructure.repositories.contexts.fts_search import (
    search_context_fts,
)
from app.memory.infrastructure.repositories.contexts.vector_search import (
    search_context_vectors,
)
from sqlalchemy.ext.asyncio import AsyncSession


class ContextSearchStore:
    """Own SQL FTS and vector recall over Context chunks."""

    def __init__(self, session: AsyncSession) -> None:
        """Create the Context search store.

        Args:
            session: Active async database session.
        """
        self._session = session

    async def ensure_search_tables(self) -> None:
        """Create virtual search tables not represented by ORM metadata."""
        await ensure_context_chunk_fts_table(session=self._session)

    async def search_fts(
        self,
        recall: ContextFtsRecall,
    ) -> list[ContextSearchMatch]:
        """Search Context chunks with SQLite FTS.

        Args:
            recall: Structured FTS recall contract.

        Returns:
            Ranked Context matches.
        """
        await self.ensure_search_tables()
        return await search_context_fts(self._session, recall)

    async def search_vector(
        self,
        recall: ContextVectorRecall,
    ) -> list[ContextSearchMatch]:
        """Search Context chunks by vector similarity.

        Args:
            recall: Structured vector recall contract.

        Returns:
            Ranked Context matches.
        """
        return await search_context_vectors(self._session, recall)
