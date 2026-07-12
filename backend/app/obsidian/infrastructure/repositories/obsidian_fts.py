"""SQLite FTS helpers for Obsidian vault search."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from app.obsidian.domain.event_enum.obsidian_enums import AlexandriaNoteType
from app.shared.utils.text_metrics import extract_word_tokens
from sqlalchemy import Select, bindparam, column, delete, func, select, table, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.dml import Delete
from sqlalchemy.sql.elements import ColumnElement

MAX_FTS_TOKEN_COUNT = 32
MAX_FTS_TOKEN_LENGTH = 64

OBSIDIAN_CHUNK_FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS obsidian_chunk_fts USING fts5(
    chunk_id UNINDEXED,
    note_id UNINDEXED,
    title,
    body,
    heading_path,
    alexandria_type,
    project,
    status,
    tags,
    relative_path,
    tokenize='porter'
);
"""

OBSIDIAN_CHUNK_FTS_TABLE = table(
    "obsidian_chunk_fts",
    column("chunk_id"),
    column("note_id"),
    column("title"),
    column("body"),
    column("heading_path"),
    column("alexandria_type"),
    column("project"),
    column("status"),
    column("tags"),
    column("relative_path"),
)

OBSIDIAN_FILES_TABLE = table(
    "obsidian_files",
    column("note_id"),
    column("index_status"),
)

type ObsidianFtsRow = tuple[str, str, float]
type ObsidianFtsStatement = Select[ObsidianFtsRow]
type ObsidianFtsParameter = str | int | list[str]


@dataclass(frozen=True, slots=True)
class ObsidianFtsQuery:
    """SQL statement and parameters for one Obsidian FTS query."""

    statement: ObsidianFtsStatement
    parameters: dict[str, ObsidianFtsParameter]


def normalize_fts_query(raw_query: str) -> str | None:
    """Normalize untrusted text into a safe FTS5 prefix query.

    Args:
        raw_query: Raw user query text.

    Returns:
        Safe FTS5 query string, or None when no searchable terms remain.
    """
    tokens = extract_word_tokens(
        raw_query.strip(),
        max_tokens=MAX_FTS_TOKEN_COUNT,
        max_token_length=MAX_FTS_TOKEN_LENGTH,
    )
    if not tokens:
        return None
    return " ".join(f'"{token}"*' for token in tokens)


async def ensure_obsidian_chunk_fts_table(*, session: AsyncSession) -> None:
    """Create the Obsidian FTS table if needed.

    Args:
        session: Active SQLAlchemy session.
    """
    await session.execute(text(OBSIDIAN_CHUNK_FTS_SQL))


def delete_obsidian_fts_statement() -> Delete:
    """Build a delete statement for all FTS rows for one note.

    Returns:
        SQLAlchemy delete statement parameterized by note_id.
    """
    return delete(OBSIDIAN_CHUNK_FTS_TABLE).where(
        OBSIDIAN_CHUNK_FTS_TABLE.c.note_id == bindparam("note_id")
    )


def build_obsidian_fts_query(
    query: str,
    *,
    limit: int,
    alexandria_type: AlexandriaNoteType | None = None,
    excluded_alexandria_types: list[AlexandriaNoteType] | None = None,
    project: str | None = None,
    tags: list[str] | None = None,
) -> ObsidianFtsQuery | None:
    """Build a safe Obsidian FTS query from user input.

    Args:
        query: User query text.
        limit: Maximum result count.
        alexandria_type: Optional note type filter.
        excluded_alexandria_types: Optional note types to omit.
        project: Optional project filter.
        tags: Optional required tags.

    Returns:
        SQL statement bundle, or None when query has no searchable terms.
    """
    normalized = normalize_fts_query(query)
    if normalized is None:
        return None
    fts_table = OBSIDIAN_CHUNK_FTS_TABLE
    fts_match_target = fts_table.table_valued()
    rank = cast(ColumnElement[float], func.bm25(fts_match_target).label("rank"))
    statement = select(fts_table.c.chunk_id, fts_table.c.note_id, rank).where(
        fts_match_target.op("MATCH")(bindparam("query"))
    )
    statement = statement.join(
        OBSIDIAN_FILES_TABLE,
        fts_table.c.note_id == OBSIDIAN_FILES_TABLE.c.note_id,
    ).where(OBSIDIAN_FILES_TABLE.c.index_status == bindparam("indexed_status"))
    parameters: dict[str, ObsidianFtsParameter] = {
        "query": normalized,
        "limit": limit,
        "indexed_status": "indexed",
    }
    if alexandria_type is not None:
        statement = statement.where(
            fts_table.c.alexandria_type == bindparam("alexandria_type")
        )
        parameters["alexandria_type"] = alexandria_type.value
    if excluded_alexandria_types:
        statement = statement.where(
            fts_table.c.alexandria_type.not_in(
                bindparam("excluded_alexandria_types", expanding=True)
            )
        )
        parameters["excluded_alexandria_types"] = [
            note_type.value for note_type in excluded_alexandria_types
        ]
    if project is not None:
        statement = statement.where(fts_table.c.project == bindparam("project"))
        parameters["project"] = project
    if tags:
        tag_query = " ".join(tags)
        statement = statement.where(fts_table.c.tags.like(bindparam("tag_query")))
        parameters["tag_query"] = f"%{tag_query}%"
    statement = statement.order_by(rank.asc()).limit(bindparam("limit"))
    return ObsidianFtsQuery(
        statement=cast(ObsidianFtsStatement, statement),
        parameters=parameters,
    )
