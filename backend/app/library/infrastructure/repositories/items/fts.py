"""FTS query and payload builders for library item repository operations."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.library.domain.event_enum.item_enums import ItemType
from app.library.infrastructure.models.item_models import LibraryItemORM
from app.shared.types.extra_types import JSONValue

FTS_TOKEN_PATTERN = re.compile(r"\w+")


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
    """SQL text and parameters for a normalized FTS search."""

    sql: str
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
        details=str(details),
    )
    return payload


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
    tokens = FTS_TOKEN_PATTERN.findall(query.strip())
    if not tokens:
        return None

    normalized = " ".join(f"{token}*" for token in tokens)
    sql = "SELECT item_id FROM item_search_fts WHERE item_search_fts MATCH :query"
    if item_type is not None:
        sql += " AND item_type = :item_type"

    fts_query = ItemFtsQuery(
        sql=sql,
        parameters={
            "query": normalized,
            "item_type": item_type.value if item_type is not None else None,
        },
    )
    return fts_query
