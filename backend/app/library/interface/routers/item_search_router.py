"""Thin candidate search routes for library items."""

from __future__ import annotations

from app.container import ApplicationContainer
from app.library.application.item_search_service import ItemSearchService
from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.library.domain.event_enum.prompt_enums import PromptKind
from app.library.domain.event_enum.search_enums import (
    SearchContentMode,
    SearchStrategy,
)
from app.library.domain.event_enum.skill_enums import RiskLevel
from app.library.interface.schemas.item.item_search_schema import ItemSearchResponse
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import LIBRARY_ROUTE_EXCEPTION_MAPPING
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, status

router = APIRouter(prefix="/library/search", tags=["library-search"])


@router.get(
    "",
    response_model=ItemSearchResponse,
    description=(
        "Search library items as lightweight candidates. Broad search never "
        "returns full content; load selected items through detail endpoints."
    ),
    status_code=status.HTTP_200_OK,
    summary="Search library candidates",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def search_library_candidates(
    q: str | None = Query(default=None),
    item_type: ItemType | None = Query(default=None),
    item_types: list[ItemType] | None = Query(default=None),
    category_id: str | None = Query(default=None),
    include_descendant_categories: bool = Query(default=False),
    tags_any: list[str] | None = Query(default=None),
    tags_all: list[str] | None = Query(default=None),
    status_filter: ItemStatus | None = Query(default=None, alias="status"),
    prompt_kind: PromptKind | None = Query(default=None),
    risk_level: RiskLevel | None = Query(default=None),
    required_tools: list[str] | None = Query(default=None),
    source_type: SourceType | None = Query(default=None),
    created_by_type: CreatedByType | None = Query(default=None),
    created_by_name: str | None = Query(default=None),
    search_fields: list[str] | None = Query(default=None),
    strategy: SearchStrategy = Query(default=SearchStrategy.DEFAULT),
    content_mode: SearchContentMode = Query(default=SearchContentMode.CANDIDATE),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: ItemSearchService = Depends(
        Provide[ApplicationContainer.library.item_search_service]
    ),
) -> ItemSearchResponse:
    """Search library candidates without full content.

    Args:
        q: Optional search text.
        item_type: Optional single type filter.
        item_types: Optional repeated type filters.
        category_id: Optional category filter.
        include_descendant_categories: Accepted for contract compatibility.
        tags_any: Tags where at least one must match.
        tags_all: Tags where all must match.
        status_filter: Optional item status filter.
        prompt_kind: Optional prompt kind filter.
        risk_level: Optional skill risk filter.
        required_tools: Required skill tools.
        source_type: Optional item source filter.
        created_by_type: Optional creator type filter.
        created_by_name: Optional creator display name filter.
        search_fields: Optional field hints for search strategy.
        strategy: Search strategy hint.
        content_mode: Content mode, restricted to candidate.
        limit: Page size.
        offset: Page offset.
        service: Candidate search service.

    Returns:
        Candidate search response.
    """
    payload = await service.search(
        query=q,
        item_type=item_type,
        item_types=item_types,
        category_id=category_id,
        include_descendant_categories=include_descendant_categories,
        tags_any=_split_query_values(tags_any),
        tags_all=_split_query_values(tags_all),
        status=status_filter,
        prompt_kind=prompt_kind,
        risk_level=risk_level,
        required_tools=_split_query_values(required_tools),
        source_type=source_type,
        created_by_type=created_by_type,
        created_by_name=created_by_name,
        search_fields=_split_query_values(search_fields),
        strategy=strategy,
        content_mode=content_mode,
        limit=limit,
        offset=offset,
    )
    validation = ItemSearchResponse.model_validate(payload)
    return validation


def _split_query_values(values: list[str] | None) -> list[str]:
    """Normalize repeated or comma-separated query values.

    Args:
        values: Raw query values from FastAPI.

    Returns:
        Trimmed non-empty values.
    """
    if values is None:
        return []
    normalized: list[str] = []
    for value in values:
        normalized.extend(part.strip() for part in value.split(",") if part.strip())
    return normalized
