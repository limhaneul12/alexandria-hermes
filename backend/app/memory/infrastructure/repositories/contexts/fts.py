"""FTS helpers for Context Vault retrieval."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import cast

from app.memory.domain.event_enum.context_enums import ContextKind, ContextScope
from sqlalchemy import (
    Select,
    bindparam,
    column,
    delete,
    func,
    insert,
    select,
    table,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.dml import Delete, Insert
from sqlalchemy.sql.elements import ColumnElement

FTS_TOKEN_PATTERN = re.compile(r"\w+")
MAX_FTS_TOKEN_COUNT = 32
MAX_FTS_TOKEN_LENGTH = 64

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

CONTEXT_CHUNK_FTS_TABLE = table(
    "context_chunk_fts",
    column("chunk_id"),
    column("context_id"),
    column("title"),
    column("summary"),
    column("content"),
    column("kind"),
    column("project"),
    column("scope"),
    column("workspace_id"),
    column("agent_id"),
    column("user_id"),
    column("session_id"),
    column("source_agent"),
    column("tags"),
    column("heading"),
)

type ContextFtsRow = tuple[str, str, float]
type ContextFtsStatement = Select[ContextFtsRow]
type ContextFtsParameter = str | int | list[str]


@dataclass(frozen=True, slots=True)
class ContextFtsQuery:
    """SQLAlchemy statement and bind parameters for a context FTS query."""

    statement: ContextFtsStatement
    parameters: dict[str, ContextFtsParameter]


def normalize_fts_query(raw_query: str) -> str | None:
    """Normalize untrusted text into a literal-token SQLite FTS5 query.

    Args:
        raw_query: User-provided search text.

    Returns:
        FTS5 query string with literal prefix tokens, or None when empty.
    """
    tokens = [
        token[:MAX_FTS_TOKEN_LENGTH]
        for token in FTS_TOKEN_PATTERN.findall(raw_query.strip())[:MAX_FTS_TOKEN_COUNT]
    ]
    if not tokens:
        return None
    normalized = " ".join(f'"{token}"*' for token in tokens)
    return normalized


async def ensure_context_chunk_fts_table(*, session: AsyncSession) -> None:
    """Create the Context Vault FTS5 virtual table when needed.

    Args:
        session: Active async database session.

    Returns:
        None.
    """
    # SQLite FTS5 virtual-table DDL has no SQLAlchemy ORM equivalent. Keep this
    # as a constant schema statement only; never concatenate user-provided data.
    await session.execute(text(CONTEXT_CHUNK_FTS_SQL))


def delete_chunk_fts_statement() -> Delete:
    """Build a bound Core delete statement for one FTS chunk row.

    Returns:
        SQLAlchemy delete statement.
    """
    return delete(CONTEXT_CHUNK_FTS_TABLE).where(
        CONTEXT_CHUNK_FTS_TABLE.c.chunk_id == bindparam("chunk_id")
    )


def delete_context_fts_statement() -> Delete:
    """Build a bound Core delete statement for all FTS rows of a context.

    Returns:
        SQLAlchemy delete statement.
    """
    return delete(CONTEXT_CHUNK_FTS_TABLE).where(
        CONTEXT_CHUNK_FTS_TABLE.c.context_id == bindparam("context_id")
    )


def insert_chunk_fts_statement() -> Insert:
    """Build a Core insert statement for one FTS chunk row.

    Returns:
        SQLAlchemy insert statement.
    """
    return insert(CONTEXT_CHUNK_FTS_TABLE).values(
        chunk_id=bindparam("chunk_id"),
        context_id=bindparam("context_id"),
        title=bindparam("title"),
        summary=bindparam("summary"),
        content=bindparam("content"),
        kind=bindparam("kind"),
        project=bindparam("project"),
        source_agent=bindparam("source_agent"),
        tags=bindparam("tags"),
        scope=bindparam("scope"),
        workspace_id=bindparam("workspace_id"),
        agent_id=bindparam("agent_id"),
        user_id=bindparam("user_id"),
        session_id=bindparam("session_id"),
        heading=bindparam("heading"),
    )


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
    normalized = normalize_fts_query(query)
    if normalized is None:
        return None

    fts_table = CONTEXT_CHUNK_FTS_TABLE
    fts_match_target = fts_table.table_valued()
    rank = cast(
        ColumnElement[float],
        func.bm25(fts_match_target).label("rank"),
    )
    statement = select(
        fts_table.c.chunk_id,
        fts_table.c.context_id,
        rank,
    ).where(fts_match_target.op("MATCH")(bindparam("query")))
    parameters: dict[str, ContextFtsParameter] = {"query": normalized, "limit": limit}
    if project is not None:
        statement = statement.where(fts_table.c.project == bindparam("project"))
        parameters["project"] = project
    if kind is not None:
        statement = statement.where(fts_table.c.kind == bindparam("kind"))
        parameters["kind"] = kind.value
    if include_scopes:
        statement = statement.where(
            fts_table.c.scope.in_(bindparam("scope_values", expanding=True))
        )
        parameters["scope_values"] = [scope.value for scope in include_scopes]
    if workspace_id is not None:
        statement = statement.where(
            fts_table.c.workspace_id == bindparam("workspace_id")
        )
        parameters["workspace_id"] = workspace_id
    if agent_id is not None:
        statement = statement.where(fts_table.c.agent_id == bindparam("agent_id"))
        parameters["agent_id"] = agent_id
    if user_id is not None:
        statement = statement.where(fts_table.c.user_id == bindparam("user_id"))
        parameters["user_id"] = user_id
    if session_id is not None:
        statement = statement.where(fts_table.c.session_id == bindparam("session_id"))
        parameters["session_id"] = session_id
    statement = statement.order_by(rank.asc()).limit(bindparam("limit"))
    fts_query = ContextFtsQuery(
        statement=cast(ContextFtsStatement, statement),
        parameters=parameters,
    )
    return fts_query
