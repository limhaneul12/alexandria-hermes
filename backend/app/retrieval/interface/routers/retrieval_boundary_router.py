"""Routes describing retrieval role boundaries."""

from __future__ import annotations

from app.container import ApplicationContainer
from app.platform.config.app_config import AppConfig
from app.retrieval.domain.event_enum.retrieval_boundary_enums import RetrievalMode
from app.retrieval.interface.schemas.retrieval.retrieval_boundary_schema import (
    RetrievalModeResponse,
    RetrievalModeResponseList,
)
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import RETRIEVAL_ROUTE_EXCEPTION_MAPPING
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status

router = APIRouter(prefix="/retrieval/boundary", tags=["retrieval-boundary"])


@router.get(
    "/modes",
    response_model=RetrievalModeResponseList,
    status_code=status.HTTP_200_OK,
    summary="List retrieval role modes",
    description="Expose recall/search/full-load/librarian synthesis boundaries.",
)
@router_exception_status(RETRIEVAL_ROUTE_EXCEPTION_MAPPING)
@inject
async def list_retrieval_modes(
    app_config: AppConfig = Depends(Provide[ApplicationContainer.app_config]),
) -> RetrievalModeResponseList:
    """Return explicit retrieval role modes for UI/agent guardrails.

    Args:
        app_config: Application config dependency used to satisfy router DI style.

    Returns:
        Retrieval mode descriptions for UI and agent guardrails.
    """
    _ = app_config
    modes = [
        RetrievalModeResponse(
            mode=RetrievalMode.CONTEXT_RECALL,
            description="Recall durable Context Vault entries as context-pack hits.",
            default_endpoint="/memory/contexts/retrieval/search",
            returns_full_content=False,
            uses_librarian=False,
        ),
        RetrievalModeResponse(
            mode=RetrievalMode.CONTEXT_RAG_SYNTHESIS,
            description="Synthesize retrieved memory when long-term judgment is needed.",
            default_endpoint="/memory/contexts/retrieval/search",
            returns_full_content=False,
            uses_librarian=False,
        ),
        RetrievalModeResponse(
            mode=RetrievalMode.LIBRARY_CANDIDATE_SEARCH,
            description="Find lightweight skill/prompt/library candidates first.",
            default_endpoint="/library/search",
            returns_full_content=False,
            uses_librarian=False,
        ),
        RetrievalModeResponse(
            mode=RetrievalMode.SELECTED_ITEM_FULL_LOAD,
            description="Load full content only for one selected skill/prompt/item id.",
            default_endpoint="/library/items/{item_id}",
            returns_full_content=True,
            uses_librarian=False,
        ),
        RetrievalModeResponse(
            mode=RetrievalMode.LIBRARIAN_SYNTHESIS,
            description="Ask a librarian with a budgeted packet when curation is needed.",
            default_endpoint="/librarians/ask",
            returns_full_content=False,
            uses_librarian=True,
        ),
    ]
    validation = RetrievalModeResponseList.model_validate(modes)
    return validation
