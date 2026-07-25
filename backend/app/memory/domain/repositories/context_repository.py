"""Composite compatibility port for Context storage and retrieval."""

from __future__ import annotations

from app.memory.domain.repositories.context_record_mutation_repository import (
    IContextRecordMutationRepository,
)
from app.memory.domain.repositories.context_record_query_repository import (
    IContextRecordQueryRepository,
)
from app.memory.domain.repositories.context_search_source import IContextSearchSource


class IContextRepository(
    IContextRecordQueryRepository,
    IContextRecordMutationRepository,
    IContextSearchSource,
):
    """Combine focused Context persistence ports for application compatibility."""
