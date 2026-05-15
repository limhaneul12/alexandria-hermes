"""RAG dependency health helpers."""

from __future__ import annotations

from app.library.application.retrieval.embedding_provider import (
    DEFAULT_EMBEDDING_DIMENSIONS,
    DEFAULT_EMBEDDING_MODEL,
    EmbeddingProvider,
)
from app.library.application.retrieval.sqlite_vec import probe_sqlite_vec
from app.library.domain.entities.context_read_models import RagDependencyHealth
from app.library.domain.event_enum.context_enums import RagHealthState, RagStrategy


def build_rag_dependency_health(
    embedding_provider: EmbeddingProvider | None,
    vector_retrieval_enabled: bool,
) -> RagDependencyHealth:
    """Return current RAG dependency health.

    Args:
        embedding_provider: Optional local embedding provider.
        vector_retrieval_enabled: Whether vector indexing/query paths are wired.

    Returns:
        Health state for FTS, vector, and embedding dependencies.
    """
    sqlite_vec = probe_sqlite_vec()
    embedding_state = (
        RagHealthState.HEALTHY
        if embedding_provider is not None
        else RagHealthState.DEGRADED
    )
    vector_state = (
        sqlite_vec.state if vector_retrieval_enabled else RagHealthState.DISABLED
    )
    default_strategy = (
        RagStrategy.HYBRID
        if vector_state is RagHealthState.HEALTHY
        and embedding_state is RagHealthState.HEALTHY
        else RagStrategy.FTS_ONLY
    )
    warnings = (
        [] if sqlite_vec.state is RagHealthState.HEALTHY else [sqlite_vec.message]
    )
    if not vector_retrieval_enabled:
        warnings.append(
            "Vector retrieval is not enabled in this MVP; using SQLite FTS5."
        )
    if embedding_provider is None:
        warnings.append("Embedding provider not assigned; vector recall disabled.")
    health = RagDependencyHealth(
        fts=RagHealthState.HEALTHY,
        vector=vector_state,
        embedding=embedding_state,
        default_strategy=default_strategy,
        model_name=(
            embedding_provider.model_name
            if embedding_provider is not None
            else DEFAULT_EMBEDDING_MODEL
        ),
        dimensions=(
            embedding_provider.dimensions
            if embedding_provider is not None
            else DEFAULT_EMBEDDING_DIMENSIONS
        ),
        warnings=warnings,
    )
    return health
