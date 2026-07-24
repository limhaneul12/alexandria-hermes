"""FTS helpers for Context Vault retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from app.memory.domain.contracts.context_recall_contracts import (
    ContextFtsRecall,
)
from app.memory.domain.event_enum.context_enums import ContextRecallLifecycleStatus
from app.memory.infrastructure.repositories.contexts.scope_recall_filter import (
    ScopeRecallColumns,
    scope_recall_clause,
)
from app.shared.utils.text_metrics import extract_word_tokens
from sqlalchemy import (
    Select,
    bindparam,
    column,
    delete,
    false,
    func,
    or_,
    select,
    table,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.dml import Delete
from sqlalchemy.sql.elements import ColumnElement

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

CONTEXTS_TABLE = table(
    "contexts",
    column("id"),
    column("status"),
    column("is_archived"),
)

type ContextFtsRow = tuple[str, str, float]
type ContextFtsStatement = Select[ContextFtsRow]
type ContextFtsParameter = str | int | bool | list[str]


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
    tokens = extract_word_tokens(
        raw_query.strip(),
        max_tokens=MAX_FTS_TOKEN_COUNT,
        max_token_length=MAX_FTS_TOKEN_LENGTH,
    )
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


def delete_context_fts_statement() -> Delete:
    """Build a bound Core delete statement for all FTS rows of a context.

    Returns:
        SQLAlchemy delete statement.
    """
    return delete(CONTEXT_CHUNK_FTS_TABLE).where(
        CONTEXT_CHUNK_FTS_TABLE.c.context_id == bindparam("context_id")
    )


def build_context_fts_query(recall: ContextFtsRecall) -> ContextFtsQuery | None:
    """Build a safe context FTS query from user input.

    Args:
        recall: Validated FTS query and recall filters.

    Returns:
        SQL query contract when tokenization yields searchable terms.
    """
    normalized = normalize_fts_query(recall.query)
    if normalized is None:
        return None

    fts_table = CONTEXT_CHUNK_FTS_TABLE
    fts_match_target = fts_table.table_valued()
    rank = cast(
        ColumnElement[float],
        func.bm25(fts_match_target).label("rank"),
    )
    recall_filter = recall.recall_filter
    lifecycle_statuses = recall_filter.lifecycle_statuses
    storage_statuses = ContextRecallLifecycleStatus.context_storage_values(
        lifecycle_statuses
    )
    lifecycle_conditions: list[ColumnElement[bool]] = []
    parameters: dict[str, ContextFtsParameter] = {
        "query": normalized,
        "limit": recall_filter.limit,
    }
    if storage_statuses:
        lifecycle_conditions.append(
            (CONTEXTS_TABLE.c.is_archived == bindparam("is_archived_active"))
            & CONTEXTS_TABLE.c.status.in_(bindparam("recall_statuses", expanding=True))
        )
        parameters["is_archived_active"] = False
        parameters["recall_statuses"] = list(storage_statuses)
    if (
        lifecycle_statuses is not None
        and ContextRecallLifecycleStatus.ARCHIVED in lifecycle_statuses
    ):
        lifecycle_conditions.append(
            CONTEXTS_TABLE.c.is_archived == bindparam("is_archived_requested")
        )
        parameters["is_archived_requested"] = True

    statement = (
        select(
            fts_table.c.chunk_id,
            fts_table.c.context_id,
            rank,
        )
        .join(CONTEXTS_TABLE, fts_table.c.context_id == CONTEXTS_TABLE.c.id)
        .where(
            fts_match_target.op("MATCH")(bindparam("query")),
            or_(*lifecycle_conditions) if lifecycle_conditions else false(),
        )
    )
    identity_filter = recall_filter.scope_identity
    statement = statement.where(
        scope_recall_clause(
            ScopeRecallColumns(
                scope=fts_table.c.scope,
                project=fts_table.c.project,
                agent_id=fts_table.c.agent_id,
                user_id=fts_table.c.user_id,
                session_id=fts_table.c.session_id,
                workspace_id=fts_table.c.workspace_id,
            ),
            identity_filter,
        )
    )
    parameters.update(identity_filter.sql_parameters())
    if recall_filter.kind is not None:
        statement = statement.where(fts_table.c.kind == bindparam("kind"))
        parameters["kind"] = recall_filter.kind.value
    statement = statement.order_by(rank.asc()).limit(bindparam("limit"))
    fts_query = ContextFtsQuery(
        statement=cast(ContextFtsStatement, statement),
        parameters=parameters,
    )
    return fts_query
