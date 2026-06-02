"""Vector SQL helpers for Context Vault retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from app.memory.domain.event_enum.context_enums import ContextKind, ContextScope
from app.memory.infrastructure.models.context_models import ContextChunkORM, ContextORM
from sqlalchemy import Select, bindparam, func, select
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
    *,
    query_embedding: str,
    model_name: str,
    dimensions: int,
    fingerprint_key: str,
    limit: int,
    project: str | None = None,
    kind: ContextKind | None = None,
    include_scopes: list[ContextScope] | None = None,
    workspace_id: str | None = None,
    agent_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
) -> ContextVectorQuery:
    """Build a safe vector query from precomputed embedding text.

    Args:
        query_embedding: JSON-compatible embedding vector text for sqlite-vec.
        model_name: Embedding model that produced the query vector.
        dimensions: Expected embedding dimensions.
        fingerprint_key: Current embedding generation fingerprint key.
        limit: Maximum returned matches.
        project: Optional project filter.
        kind: Optional context kind filter.
        include_scopes: Optional recall scope filters.
        workspace_id: Optional workspace filter.
        agent_id: Optional agent filter.
        user_id: Optional user filter.
        session_id: Optional session filter.

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
    parameters: dict[str, ContextVectorParameter] = {
        "query_embedding": query_embedding,
        "model_name": model_name,
        "dimensions": dimensions,
        "fingerprint_key": fingerprint_key,
        "limit": limit,
    }

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
            ContextORM.is_archived.is_(False),
        )
    )
    if project is not None:
        statement = statement.where(ContextORM.project == bindparam("project"))
        parameters["project"] = project
    if kind is not None:
        statement = statement.where(ContextORM.kind == bindparam("kind"))
        parameters["kind"] = kind.value
    if include_scopes:
        scope_values = [scope.value for scope in include_scopes]
        statement = statement.where(ContextORM.scope.in_(scope_values))
    if workspace_id is not None:
        statement = statement.where(
            ContextORM.workspace_id == bindparam("workspace_id")
        )
        parameters["workspace_id"] = workspace_id
    if agent_id is not None:
        statement = statement.where(ContextORM.agent_id == bindparam("agent_id"))
        parameters["agent_id"] = agent_id
    if user_id is not None:
        statement = statement.where(ContextORM.user_id == bindparam("user_id"))
        parameters["user_id"] = user_id
    if session_id is not None:
        statement = statement.where(ContextORM.session_id == bindparam("session_id"))
        parameters["session_id"] = session_id

    statement = statement.order_by(distance.asc()).limit(bindparam("limit"))
    vector_query = ContextVectorQuery(
        statement=cast(ContextVectorStatement, statement),
        parameters=parameters,
    )
    return vector_query
