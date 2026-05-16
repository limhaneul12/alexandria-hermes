"""Vector SQL helpers for Context Vault retrieval."""

from __future__ import annotations

from dataclasses import dataclass

from app.memory.domain.event_enum.context_enums import ContextKind, ContextScope


@dataclass(frozen=True, slots=True)
class ContextVectorQuery:
    """SQL text and bind parameters for a context vector query."""

    sql: str
    parameters: dict[str, str | int]


def build_context_vector_query(
    *,
    query_embedding: str,
    model_name: str,
    dimensions: int,
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
    sql = (
        "SELECT context_chunks.id AS chunk_id, contexts.id AS context_id, "
        "vec_distance_cosine(context_chunks.embedding, :query_embedding) AS distance "
        "FROM context_chunks "
        "JOIN contexts ON contexts.id = context_chunks.context_id "
        "WHERE context_chunks.embedding IS NOT NULL "
        "AND context_chunks.embedding_model = :model_name "
        "AND context_chunks.embedding_dimensions = :dimensions "
        "AND contexts.is_archived = 0"
    )
    parameters: dict[str, str | int] = {
        "query_embedding": query_embedding,
        "model_name": model_name,
        "dimensions": dimensions,
        "limit": limit,
    }
    if project is not None:
        sql += " AND contexts.project = :project"
        parameters["project"] = project
    if kind is not None:
        sql += " AND contexts.kind = :kind"
        parameters["kind"] = kind.value
    if include_scopes:
        scope_clauses: list[str] = []
        for index, scope in enumerate(include_scopes):
            parameter_name = f"scope_{index}"
            scope_clauses.append(f"contexts.scope = :{parameter_name}")
            parameters[parameter_name] = scope.value
        sql += f" AND ({' OR '.join(scope_clauses)})"
    if workspace_id is not None:
        sql += " AND contexts.workspace_id = :workspace_id"
        parameters["workspace_id"] = workspace_id
    if agent_id is not None:
        sql += " AND contexts.agent_id = :agent_id"
        parameters["agent_id"] = agent_id
    if user_id is not None:
        sql += " AND contexts.user_id = :user_id"
        parameters["user_id"] = user_id
    if session_id is not None:
        sql += " AND contexts.session_id = :session_id"
        parameters["session_id"] = session_id
    sql += " ORDER BY distance ASC LIMIT :limit"
    vector_query = ContextVectorQuery(sql=sql, parameters=parameters)
    return vector_query
