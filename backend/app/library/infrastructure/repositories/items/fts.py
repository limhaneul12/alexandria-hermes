"""FTS query and payload builders for library item repository operations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import cast

from app.library.domain.event_enum.item_enums import ItemType
from app.library.domain.event_enum.search_enums import LibrarySearchField
from app.library.infrastructure.models.item_models import LibraryItemORM
from app.shared.types.extra_types import JSONValue
from sqlalchemy import Select, bindparam, column, delete, func, insert, select, table
from sqlalchemy.sql.dml import Delete, Insert
from sqlalchemy.sql.elements import ColumnElement

FTS_TOKEN_PATTERN = re.compile(r"\w+")
CONTENT_DETAIL_KEYS = frozenset(
    (
        "body",
        "content",
        "expected_result",
        "markdown",
        "prompt",
        "source_text",
    )
)
ITEM_SEARCH_FTS_TABLE = table(
    "item_search_fts",
    column("item_id"),
    column("item_type"),
    column("title"),
    column("summary"),
    column("content"),
    column("tags"),
    column("details"),
)
type ItemFtsRow = tuple[str]
type ItemCandidateFtsRow = tuple[str, float]
type ItemFtsStatement = Select[ItemFtsRow] | Select[ItemCandidateFtsRow]


@dataclass(frozen=True, slots=True)
class ItemFtsPayload:
    """Parameters used to upsert an item into the FTS table."""

    item_id: str
    item_type: str
    title: str
    summary: str
    content: str
    tags: str
    details: str

    def as_parameters(self) -> dict[str, str]:
        """Return SQL bind parameters for the FTS insert statement.

        Returns:
            dict[str, str]: Value produced by as_parameters.
        """
        parameters = {
            "item_id": self.item_id,
            "item_type": self.item_type,
            "title": self.title,
            "summary": self.summary,
            "content": self.content,
            "tags": self.tags,
            "details": self.details,
        }
        return parameters


@dataclass(frozen=True, slots=True)
class ItemFtsQuery:
    """SQLAlchemy statement and parameters for a normalized FTS search."""

    statement: ItemFtsStatement
    parameters: dict[str, str | None]


def _details_from_item(item: LibraryItemORM) -> dict[str, JSONValue]:
    details = item.details
    item_details = details if isinstance(details, dict) else {}
    return item_details


def _tags_text_from(details: dict[str, JSONValue], item: LibraryItemORM) -> str:
    tags = details.get("tags", item.tags)
    if isinstance(tags, list):
        tags_text = " ".join(str(tag) for tag in tags)
    else:
        tags_text = ""
    return tags_text


def _content_text_from(details: dict[str, JSONValue], item: LibraryItemORM) -> str:
    content_text = " ".join(
        str(value)
        for value in [
            details.get("content", item.content),
            details.get("purpose", ""),
            details.get("summary", item.summary),
            details.get("body", ""),
            details.get("expected_result", ""),
        ]
        if value
    )
    return content_text


def _details_text_from(details: dict[str, JSONValue]) -> str:
    """Return metadata-safe detail text for default candidate search.

    Args:
        details: Item detail payload.

    Returns:
        Text from non-body metadata fields.
    """
    values: list[str] = []
    for key, value in details.items():
        if key in CONTENT_DETAIL_KEYS:
            continue
        if isinstance(value, str | int | float | bool):
            values.append(str(value))
        elif isinstance(value, list):
            values.extend(
                str(item)
                for item in value
                if isinstance(item, str | int | float | bool)
            )
    return " ".join(values)


def build_item_fts_payload(item: LibraryItemORM) -> ItemFtsPayload:
    """Build normalized FTS insert payload from one item row.

    Args:
        item [LibraryItemORM]: Value supplied to build_item_fts_payload.

    Returns:
        ItemFtsPayload: Value produced by build_item_fts_payload.
    """
    details = _details_from_item(item)
    payload = ItemFtsPayload(
        item_id=item.id,
        item_type=item.item_type,
        title=item.title,
        summary="" if item.summary is None else item.summary,
        content=_content_text_from(details, item),
        tags=_tags_text_from(details, item),
        details=_details_text_from(details),
    )
    return payload


def delete_item_fts_statement() -> Delete:
    """Build a bound Core delete statement for one FTS item row.

    Returns:
        SQLAlchemy delete statement.
    """
    return delete(ITEM_SEARCH_FTS_TABLE).where(
        ITEM_SEARCH_FTS_TABLE.c.item_id == bindparam("item_id")
    )


def insert_item_fts_statement() -> Insert:
    """Build a bound Core insert statement for one FTS item row.

    Returns:
        SQLAlchemy insert statement.
    """
    return insert(ITEM_SEARCH_FTS_TABLE).values(
        item_id=bindparam("item_id"),
        item_type=bindparam("item_type"),
        title=bindparam("title"),
        summary=bindparam("summary"),
        content=bindparam("content"),
        tags=bindparam("tags"),
        details=bindparam("details"),
    )


def normalize_item_fts_query(query: str) -> str | None:
    """Normalize untrusted item search text into literal FTS5 prefix tokens.

    Args:
        query: Raw user search text.

    Returns:
        FTS5 query string with literal prefix tokens, or None when no tokens exist.
    """
    tokens = FTS_TOKEN_PATTERN.findall(query.strip())
    if not tokens:
        return None
    return " ".join(f'"{token}"*' for token in tokens)


def build_item_fts_query(
    query: str, item_type: ItemType | None = None
) -> ItemFtsQuery | None:
    """Build a safe FTS query from raw user search text.

    Args:
        query [str]: Value supplied to build_item_fts_query.
        item_type [ItemType | None]: Value supplied to build_item_fts_query.

    Returns:
        ItemFtsQuery | None: Value produced by build_item_fts_query.
    """
    normalized = normalize_item_fts_query(query)
    if normalized is None:
        return None

    fts_table = ITEM_SEARCH_FTS_TABLE
    fts_match_target = fts_table.table_valued()
    statement = select(fts_table.c.item_id).where(
        fts_match_target.op("MATCH")(bindparam("query"))
    )
    if item_type is not None:
        statement = statement.where(fts_table.c.item_type == bindparam("item_type"))

    fts_query = ItemFtsQuery(
        statement=cast(Select[ItemFtsRow], statement),
        parameters={
            "query": normalized,
            "item_type": item_type.value if item_type is not None else None,
        },
    )
    return fts_query


def build_item_candidate_fts_query(
    query: str,
    search_fields: tuple[LibrarySearchField, ...],
) -> ItemFtsQuery | None:
    """Build a ranked FTS subquery for candidate search.

    Args:
        query: Raw user search text.
        search_fields: FTS columns allowed for matching.

    Returns:
        Ranked FTS query, or ``None`` when the input has no searchable tokens.
    """
    normalized = normalize_item_fts_query(query)
    if normalized is None:
        return None

    columns = " ".join(field.value for field in search_fields)
    field_scoped_query = f"{{{columns}}} : ({normalized})"
    fts_table = ITEM_SEARCH_FTS_TABLE
    fts_match_target = fts_table.table_valued()
    rank = cast(
        ColumnElement[float],
        func.bm25(fts_match_target).label("rank"),
    )
    statement = select(
        fts_table.c.item_id.label("item_id"),
        rank,
    ).where(fts_match_target.op("MATCH")(bindparam("query")))
    fts_query = ItemFtsQuery(
        statement=cast(Select[ItemCandidateFtsRow], statement),
        parameters={
            "query": field_scoped_query,
            "item_type": None,
        },
    )
    return fts_query
