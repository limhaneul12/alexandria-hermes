"""FTS helpers for Context Vault retrieval."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.library.domain.event_enum.context_enums import ContextKind

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
) -> ContextFtsQuery | None:
    """Build a safe context FTS query from user input.

    Args:
        query: Raw search query.
        limit: Maximum returned matches.
        project: Optional project filter.
        kind: Optional context kind filter.

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
    sql += " ORDER BY rank LIMIT :limit"
    fts_query = ContextFtsQuery(sql=sql, parameters=parameters)
    return fts_query
