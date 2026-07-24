"""Vector SQL helpers for Context Vault retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from app.memory.domain.contracts.context_recall_contracts import (
    ContextVectorRecall,
)
from app.memory.domain.event_enum.context_enums import ContextRecallLifecycleStatus
from app.memory.infrastructure.models.context_models import ContextChunkORM, ContextORM
from app.memory.infrastructure.repositories.contexts.scope_recall_filter import (
    ScopeRecallColumns,
    scope_recall_clause,
)
from sqlalchemy import Select, bindparam, false, func, or_, select
from sqlalchemy.sql.elements import ColumnElement

type ContextVectorRow = tuple[str, str, float]
type ContextVectorStatement = Select[ContextVectorRow]
type ContextVectorParameter = str | int


@dataclass(frozen=True, slots=True)
class ContextVectorQuery:
    """SQLAlchemy statement and bind parameters for a context vector query."""

    statement: ContextVectorStatement
    parameters: dict[str, ContextVectorParameter]


def build_context_vector_query(
    recall: ContextVectorRecall, query_embedding: str
) -> ContextVectorQuery:
    """Build a safe vector query from precomputed embedding text.

    Args:
        recall: Validated vector query and recall filters.
        query_embedding: JSON-compatible vector text for sqlite-vec.

    Returns:
        ContextVectorQuery: SQL query contract.
    """
    distance = cast(
        ColumnElement[float],
        func.vec_distance_cosine(
            ContextChunkORM.embedding,
            bindparam("query_embedding"),
        ).label("distance"),
    )
    recall_filter = recall.recall_filter
    parameters: dict[str, ContextVectorParameter] = {
        "query_embedding": query_embedding,
        "model_name": recall.model_name,
        "dimensions": recall.dimensions,
        "fingerprint_key": recall.fingerprint_key,
        "limit": recall_filter.limit,
    }
    storage_statuses = ContextRecallLifecycleStatus.context_storage_values(
        recall_filter.lifecycle_statuses
    )
    lifecycle_conditions: list[ColumnElement[bool]] = []
    if storage_statuses:
        lifecycle_conditions.append(
            ContextORM.is_archived.is_(False) & ContextORM.status.in_(storage_statuses)
        )
    if (
        recall_filter.lifecycle_statuses is not None
        and ContextRecallLifecycleStatus.ARCHIVED in recall_filter.lifecycle_statuses
    ):
        lifecycle_conditions.append(ContextORM.is_archived.is_(True))

    statement = (
        select(
            ContextChunkORM.id.label("chunk_id"),
            ContextORM.id.label("context_id"),
            distance,
        )
        .join(ContextORM, ContextORM.id == ContextChunkORM.context_id)
        .where(
            ContextChunkORM.embedding.is_not(None),
            ContextChunkORM.embedding_model == bindparam("model_name"),
            ContextChunkORM.embedding_dimensions == bindparam("dimensions"),
            ContextChunkORM.embedding_fingerprint_key == bindparam("fingerprint_key"),
            or_(*lifecycle_conditions) if lifecycle_conditions else false(),
        )
    )
    identity_filter = recall_filter.scope_identity
    context_table = ContextORM.__table__
    statement = statement.where(
        scope_recall_clause(
            ScopeRecallColumns(
                scope=context_table.c.scope,
                project=context_table.c.project,
                agent_id=context_table.c.agent_id,
                user_id=context_table.c.user_id,
                session_id=context_table.c.session_id,
                workspace_id=context_table.c.workspace_id,
            ),
            identity_filter,
        )
    )
    parameters.update(identity_filter.sql_parameters())
    if recall_filter.kind is not None:
        statement = statement.where(ContextORM.kind == bindparam("kind"))
        parameters["kind"] = recall_filter.kind.value

    statement = statement.order_by(distance.asc()).limit(bindparam("limit"))
    vector_query = ContextVectorQuery(
        statement=cast(ContextVectorStatement, statement),
        parameters=parameters,
    )
    return vector_query
