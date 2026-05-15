"""FTS helpers for Context Vault retrieval."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.memory.domain.event_enum.context_enums import ContextKind, ContextScope

FTS_TOKEN_PATTERN = re.compile(r"\w+")

CONTEXT_CHUNK_FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS context_chunk_fts USING fts5(
    chunk_id UNINDEXED,
    context_id UNINDEXED,
    title,
    summary,
    content,
    kind,
    project,
    scope,
    workspace_id,
    agent_id,
    user_id,
    session_id,
    source_agent,
    tags,
    heading,
    tokenize='porter'
);
"""


@dataclass(frozen=True, slots=True)
class ContextFtsQuery:
    """SQL text and bind parameters for a context FTS query."""

    sql: str
    parameters: dict[str, str | int | None]


def build_context_fts_query(
    query: str,
    *,
    limit: int,
    project: str | None = None,
    kind: ContextKind | None = None,
    include_scopes: list[ContextScope] | None = None,
    workspace_id: str | None = None,
    agent_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
) -> ContextFtsQuery | None:
    """Build a safe context FTS query from user input.

    Args:
        query: Raw search query.
        limit: Maximum returned matches.
        project: Optional project filter.
        kind: Optional context kind filter.
        include_scopes: Optional recall scope filters.
        workspace_id: Optional workspace filter.
        agent_id: Optional agent filter.
        user_id: Optional user filter.
        session_id: Optional session filter.

    Returns:
        SQL query contract when tokenization yields searchable terms.
    """
    tokens = FTS_TOKEN_PATTERN.findall(query.strip())
    if not tokens:
        return None

    normalized = " ".join(f"{token}*" for token in tokens)
    sql = (
        "SELECT chunk_id, context_id, bm25(context_chunk_fts) AS rank "
        "FROM context_chunk_fts WHERE context_chunk_fts MATCH :query"
    )
    parameters: dict[str, str | int | None] = {"query": normalized, "limit": limit}
    if project is not None:
        sql += " AND project = :project"
        parameters["project"] = project
    if kind is not None:
        sql += " AND kind = :kind"
        parameters["kind"] = kind.value
    if include_scopes:
        scope_clauses: list[str] = []
        for index, scope in enumerate(include_scopes):
            parameter_name = f"scope_{index}"
            scope_clauses.append(f"scope = :{parameter_name}")
            parameters[parameter_name] = scope.value
        sql += f" AND ({' OR '.join(scope_clauses)})"
    if workspace_id is not None:
        sql += " AND workspace_id = :workspace_id"
        parameters["workspace_id"] = workspace_id
    if agent_id is not None:
        sql += " AND agent_id = :agent_id"
        parameters["agent_id"] = agent_id
    if user_id is not None:
        sql += " AND user_id = :user_id"
        parameters["user_id"] = user_id
    if session_id is not None:
        sql += " AND session_id = :session_id"
        parameters["session_id"] = session_id
    sql += " ORDER BY rank LIMIT :limit"
    fts_query = ContextFtsQuery(sql=sql, parameters=parameters)
    return fts_query
