"""Librarian runtime operations: recommend/classify/candidate generation."""

from __future__ import annotations

from app.connections.application.librarian_service import LibrarianService
from app.container import ApplicationContainer
from app.librarian.application.hermes_collaboration_service import (
    HermesCollaborationService,
)
from app.librarian.interface.schemas.librarian.hermes_collaboration_schemas import (
    AskLibrarianRequest,
    AskLibrarianResponse,
    LibrarianJobStatusResponse,
)
from app.librarian.interface.schemas.librarian.librarian_ops_schemas import (
    ClassifyRequest,
    CreateCandidateRequest,
    RecommendRequest,
)
from app.library.application.item_service import ItemService
from app.library.domain.event_enum.item_enums import ItemType
from app.library.interface.schemas.item.item_schema import (
    ClassificationResponse,
    ItemResponse,
    ItemResponseList,
)
from app.platform.security.operator_api_key import require_operator_api_key
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import LIBRARY_ROUTE_EXCEPTION_MAPPING
from app.shared.types.types_convert_utils import now_utc
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status

router = APIRouter(
    prefix="/librarians",
    tags=["librarian"],
    dependencies=[Depends(require_operator_api_key)],
)


@router.post(
    "/route-preview",
    response_model=AskLibrarianResponse,
    description="Preview librarian routing without queueing delegation.",
    status_code=status.HTTP_200_OK,
    summary="Preview librarian route",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def route_preview(
    request: AskLibrarianRequest,
    collaboration_service: HermesCollaborationService = Depends(
        Provide[ApplicationContainer.librarian.hermes_collaboration_service]
    ),
) -> AskLibrarianResponse:
    """Preview the self-acquisition/librarian route for a Hermes prompt.

    Args:
        request: Ask-librarian request.
        collaboration_service: Collaboration service.

    Returns:
        AskLibrarianResponse: Guidance with route_preview populated.
    """
    command = request.model_copy(update={"delegate_to_librarian": False}).to_command()
    payload = await collaboration_service.ask_librarian(command)
    validation = AskLibrarianResponse.model_validate(payload)
    return validation


@router.post(
    "/ask",
    response_model=AskLibrarianResponse,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Ask librarian",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def ask_librarian(
    request: AskLibrarianRequest,
    collaboration_service: HermesCollaborationService = Depends(
        Provide[ApplicationContainer.librarian.hermes_collaboration_service]
    ),
) -> AskLibrarianResponse:
    """Return Hermes self-acquisition or librarian delegation guidance.

    Args:
        request [AskLibrarianRequest]: Value supplied to ask_librarian.
        collaboration_service [HermesCollaborationService]: Value supplied to ask_librarian.

    Returns:
        AskLibrarianResponse: Value produced by ask_librarian.
    """
    payload = await collaboration_service.ask_librarian(request.to_command())
    validation = AskLibrarianResponse.model_validate(payload)
    return validation


@router.get(
    "/jobs/{job_id}",
    response_model=LibrarianJobStatusResponse,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Librarian job status",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def librarian_job_status(
    job_id: str,
    collaboration_service: HermesCollaborationService = Depends(
        Provide[ApplicationContainer.librarian.hermes_collaboration_service]
    ),
) -> LibrarianJobStatusResponse:
    """Return status for a guidance-only librarian request.

    Args:
        job_id [str]: Value supplied to librarian_job_status.
        collaboration_service [HermesCollaborationService]: Value supplied to librarian_job_status.

    Returns:
        LibrarianJobStatusResponse: Value produced by librarian_job_status.
    """
    payload = await collaboration_service.job_status(job_id)
    validation = LibrarianJobStatusResponse.model_validate(payload)
    return validation


@router.post(
    "/recommend",
    response_model=ItemResponseList,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Recommend",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def recommend(
    request: RecommendRequest,
    item_service: ItemService = Depends(
        Provide[ApplicationContainer.library.item_service]
    ),
) -> ItemResponseList:
    """Recommend items by query with simple keyword search fallback.

    Args:
        request [RecommendRequest]: Value supplied to recommend.
        item_service [ItemService]: Value supplied to recommend.

    Returns:
        ItemResponseList: Value produced by recommend.
    """
    items = await item_service.search(query=request.query, item_type=request.item_type)
    validation = ItemResponseList.model_validate(items[: request.limit])
    return validation


@router.post(
    "/classify",
    response_model=ClassificationResponse,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Classify",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def classify(
    request: ClassifyRequest,
    librarian_service: LibrarianService = Depends(
        Provide[ApplicationContainer.connections.librarian_service]
    ),
) -> ClassificationResponse:
    """Classify prompt into rough taxonomy categories.

    Args:
        request [ClassifyRequest]: Value supplied to classify.
        librarian_service [LibrarianService]: Value supplied to classify.

    Returns:
        ClassificationResponse: Value produced by classify.
    """
    # Keep the route DI shape consistent while classification is still inline.
    _ = librarian_service
    lowered = request.text.lower()
    if "workflow" in lowered:
        return ClassificationResponse(label=ItemType.WORKFLOW, confidence=0.76)
    if "api" in lowered or "agent" in lowered:
        return ClassificationResponse(label=ItemType.SKILL, confidence=0.83)
    return ClassificationResponse(label=ItemType.KNOWLEDGE, confidence=0.55)


@router.post(
    "/create-skill-candidate",
    response_model=ItemResponse,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Create skill candidate",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def create_skill_candidate(
    request: CreateCandidateRequest,
    librarian_service: LibrarianService = Depends(
        Provide[ApplicationContainer.connections.librarian_service]
    ),
) -> ItemResponse:
    """Generate candidate payload and return draft candidate.

    Args:
        request [CreateCandidateRequest]: Value supplied to create_skill_candidate.
        librarian_service [LibrarianService]: Value supplied to create_skill_candidate.

    Returns:
        ItemResponse: Value produced by create_skill_candidate.
    """
    candidate = librarian_service.generate_candidate_stub(
        provider_id=request.provider_id,
        prompt=request.prompt,
    )
    # Keep API shape as draft skill candidate without persistence.
    now = now_utc()
    candidate_payload = candidate.to_candidate_payload()
    result = {
        "id": "draft-skill-candidate",
        "item_type": "SKILL",
        "title": candidate_payload["title"],
        "summary": candidate_payload["summary"],
        "content": candidate_payload["content"],
        "category_id": request.category_id,
        "tags": ["draft", "librarian"],
        "details": {
            "purpose": candidate_payload["purpose"],
            "input_schema": candidate_payload["input_schema"],
            "output_schema": candidate_payload["output_schema"],
            "required_tools": candidate_payload["required_tools"],
            "risk_level": candidate_payload["risk_level"],
            "version": candidate_payload["version"],
        },
        "status": "DRAFT",
        "source_type": "LIBRARIAN_CREATED",
        "created_by_type": "LIBRARIAN",
        "created_by_name": "librarian",
        "created_at": now,
        "updated_at": now,
    }
    validation = ItemResponse.model_validate(result)
    return validation
