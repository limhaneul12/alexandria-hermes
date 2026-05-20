"""Application service for thin library candidate search."""

from __future__ import annotations

from datetime import datetime

from app.library.domain.entities.item_search_hit import (
    ItemSearchCandidate,
    ItemSearchHit,
)
from app.library.domain.entities.item_search_query import ItemSearchQuery
from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.library.domain.event_enum.prompt_enums import PromptKind
from app.library.domain.event_enum.search_enums import (
    CommonPreviewKey,
    LibrarySearchField,
    PromptPreviewKey,
    SearchContentMode,
    SearchStrategy,
    SkillPreviewKey,
)
from app.library.domain.event_enum.skill_enums import RiskLevel
from app.library.domain.repositories.item_repository import IItemRepository
from app.library.domain.types.item_search_payload_types import (
    ItemSearchResultPayload,
)
from app.shared.exceptions import LibraryValidationError
from app.shared.types.extra_types import JSONObject, JSONValue
from app.shared.utils.text_metrics import extract_word_tokens

DEFAULT_SEARCH_LIMIT = 20
MAX_SEARCH_LIMIT = 100
MAX_HIGHLIGHTS = 3


class ItemSearchService:
    """Coordinate library candidate discovery without full content payloads."""

    def __init__(self, item_repo: IItemRepository) -> None:
        """Initialize service dependencies.

        Args:
            item_repo: Repository used for candidate projections.
        """
        self.item_repo = item_repo

    async def search(
        self,
        query: str | None = None,
        item_type: ItemType | None = None,
        item_types: list[ItemType] | None = None,
        category_id: str | None = None,
        include_descendant_categories: bool = False,
        tags_any: list[str] | None = None,
        tags_all: list[str] | None = None,
        status: ItemStatus | None = None,
        prompt_kind: PromptKind | None = None,
        risk_level: RiskLevel | None = None,
        required_tools: list[str] | None = None,
        source_type: SourceType | None = None,
        created_by_type: CreatedByType | None = None,
        created_by_name: str | None = None,
        updated_after: datetime | None = None,
        updated_before: datetime | None = None,
        search_fields: list[str] | None = None,
        strategy: SearchStrategy = SearchStrategy.DEFAULT,
        content_mode: SearchContentMode = SearchContentMode.CANDIDATE,
        limit: int = DEFAULT_SEARCH_LIMIT,
        offset: int = 0,
    ) -> ItemSearchResultPayload:
        """Search library items as thin candidates.

        Args:
            query: Optional search text.
            item_type: Optional single item type filter.
            item_types: Optional multi-type filter.
            category_id: Optional category filter.
            tags_any: Candidate must include at least one of these tags.
            tags_all: Candidate must include all of these tags.
            status: Optional lifecycle status filter.
            prompt_kind: Optional prompt kind filter.
            risk_level: Optional skill risk filter.
            required_tools: Required skill tools that must be present.
            source_type: Optional source type filter.
            created_by_type: Optional creator kind filter.
            created_by_name: Optional creator display-name filter.
            updated_after: Optional inclusive updated-at lower bound.
            updated_before: Optional inclusive updated-at upper bound.
            search_fields: Optional field hints for future strategy selection.
        strategy: Candidate search strategy.
            content_mode: Broad search content mode; only candidate is allowed.
            limit: Requested page size.
            offset: Requested row offset.

        Returns:
            Candidate search result payload.
        """
        if content_mode is not SearchContentMode.CANDIDATE:
            raise LibraryValidationError(
                "Broad library search only returns candidate content; "
                "use selected item endpoints for full content."
            )

        normalized_types = _normalize_item_types(item_type, item_types)
        normalized_query = None if query is None else query.strip()
        normalized_search_fields = _resolve_search_fields(search_fields, strategy)
        bounded_limit = min(MAX_SEARCH_LIMIT, max(1, int(limit)))
        bounded_offset = max(0, int(offset))
        options = ItemSearchQuery(
            query=normalized_query if normalized_query else None,
            item_types=normalized_types,
            category_id=category_id,
            include_descendant_categories=include_descendant_categories,
            tags_any=_clean_tuple(tags_any),
            tags_all=_clean_tuple(tags_all),
            status=status,
            prompt_kind=prompt_kind,
            risk_level=risk_level,
            required_tools=_clean_tuple(required_tools),
            source_type=source_type,
            created_by_type=created_by_type,
            created_by_name=created_by_name,
            updated_since=updated_after,
            updated_before=updated_before,
            search_fields=normalized_search_fields,
            limit=bounded_limit,
            offset=bounded_offset,
        )
        candidates, total = await self.item_repo.search_candidates(options)
        hits = [
            _candidate_to_hit(candidate, normalized_query).to_payload()
            for candidate in candidates
        ]
        return {
            "items": hits,
            "total": total,
            "limit": bounded_limit,
            "offset": bounded_offset,
        }


def _normalize_item_types(
    item_type: ItemType | None,
    item_types: list[ItemType] | None,
) -> tuple[ItemType, ...]:
    values: list[ItemType] = []
    if item_type is not None:
        values.append(item_type)
    if item_types is not None:
        values.extend(item_types)
    deduped: list[ItemType] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return tuple(deduped)


def _clean_tuple(values: list[str] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    return tuple(value.strip() for value in values if value.strip())


def _resolve_search_fields(
    values: list[str] | None,
    strategy: SearchStrategy,
) -> tuple[LibrarySearchField, ...]:
    requested = _clean_tuple(values)
    if not requested:
        return LibrarySearchField.default_fields()

    normalized: list[LibrarySearchField] = []
    for value in requested:
        try:
            field = LibrarySearchField.from_request_value(value)
        except ValueError as error:
            raise LibraryValidationError(
                f"Unsupported library search field: {value}"
            ) from error
        if strategy is SearchStrategy.METADATA and field is LibrarySearchField.CONTENT:
            raise LibraryValidationError(
                "metadata search does not include content body"
            )
        if field not in normalized:
            normalized.append(field)
    return tuple(normalized)


def _candidate_to_hit(
    candidate: ItemSearchCandidate,
    query: str | None,
) -> ItemSearchHit:
    why_matched, highlights = _match_explanation(candidate, query)
    return ItemSearchHit(
        id=candidate.id,
        item_type=candidate.item_type,
        title=candidate.title,
        summary=candidate.summary,
        tags=list(candidate.tags),
        status=candidate.status,
        category_id=candidate.category_id,
        score=round(float(candidate.score), 6),
        why_matched=why_matched,
        highlights=highlights,
        details_preview=_details_preview(candidate),
        content_char_count=candidate.content_char_count,
        updated_at=candidate.updated_at,
    )


def _details_preview(candidate: ItemSearchCandidate) -> JSONObject:
    if candidate.item_type is ItemType.SKILL:
        keys = SkillPreviewKey
    elif candidate.item_type is ItemType.PROMPT:
        keys = PromptPreviewKey
    else:
        keys = CommonPreviewKey
    preview: JSONObject = {}
    for key in keys:
        key_value = key.value
        if key_value not in candidate.details:
            continue
        value = candidate.details.get(key_value)
        if _is_preview_value(value):
            preview[key_value] = value
    return preview


def _match_explanation(
    candidate: ItemSearchCandidate,
    query: str | None,
) -> tuple[list[str], list[str]]:
    if query is None or not query.strip():
        return [], []
    tokens = [token.lower() for token in extract_word_tokens(query)]
    why: list[str] = []
    highlights: list[str] = []
    _append_match("title", candidate.title, tokens, why, highlights)
    _append_match("summary", candidate.summary or "", tokens, why, highlights)
    for tag in candidate.tags:
        _append_match("tags", tag, tokens, why, highlights)
    for value in _preview_strings(_details_preview(candidate)):
        _append_match("details", value, tokens, why, highlights)
    if len(why) == 0:
        why.append("content_body")
        highlights.append("Content body matched; open the item detail to inspect.")
    return why, highlights[:MAX_HIGHLIGHTS]


def _append_match(
    field: str,
    value: str,
    tokens: list[str],
    why: list[str],
    highlights: list[str],
) -> None:
    value_lower = value.lower()
    if not value_lower or not any(token in value_lower for token in tokens):
        return
    if field not in why:
        why.append(field)
    if len(highlights) < MAX_HIGHLIGHTS:
        highlights.append(value[:180])


def _preview_strings(payload: JSONObject) -> list[str]:
    values: list[str] = []
    for value in payload.values():
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, list):
            values.extend(str(item) for item in value if isinstance(item, str))
    return values


def _is_preview_value(value: JSONValue | None) -> bool:
    if value is None or isinstance(value, str | int | float | bool):
        return True
    if isinstance(value, list):
        return all(
            item is None or isinstance(item, str | int | float | bool) for item in value
        )
    return False
