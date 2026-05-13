"""Skill-specific routes."""

from __future__ import annotations

from app.library.application.item_service import ItemService
from app.library.application.librarian_service import LibrarianService
from app.library.application.skill_service import SkillService
from app.library.domain.entities.enums import ItemType
from app.library.interface.routers._helpers import (
    build_patch_payload,
    ensure_item_type,
)
from app.library.interface.routers.dependencies import (
    get_item_service,
    get_librarian_service,
    get_skill_service,
)
from app.library.interface.schemas.item_schema import ItemResponse
from app.library.interface.schemas.skill_schema import (
    AgentSubmitSkillRequest,
    LibrarianSkillRequest,
    SkillCreateRequest,
    SkillPatchRequest,
)
from app.shared.exceptions import LibraryResourceNotFoundError
from fastapi import APIRouter, Depends, HTTPException, Query, status

router = APIRouter(prefix="/skills", tags=["skills"])


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_skill(
    request: SkillCreateRequest,
    skill_service: SkillService = Depends(get_skill_service),
) -> ItemResponse:
    """Create one skill entry from manual input."""
    payload = await skill_service.create_skill(
        title=request.title,
        summary=request.summary,
        content=request.content,
        category_id=request.category_id,
        tags=request.tags,
        purpose=request.purpose,
        input_schema=request.input_schema,
        output_schema=request.output_schema,
        usage_example=request.usage_example,
        required_tools=request.required_tools,
        risk_level=request.risk_level,
        version=request.version,
        created_by_name=request.created_by_name,
        activate=request.status.value == "ACTIVE",
        status=request.status,
    )
    return ItemResponse.model_validate(payload)


@router.post(
    "/submit-by-agent", response_model=ItemResponse, status_code=status.HTTP_201_CREATED
)
async def submit_skill_by_agent(
    request: AgentSubmitSkillRequest,
    skill_service: SkillService = Depends(get_skill_service),
) -> ItemResponse:
    """Register structured skill payload from an external agent."""
    payload = await skill_service.create_skill_by_agent(
        title=request.title,
        content=request.content,
        summary=request.summary,
        category_id=request.category_id,
        tags=request.tags,
        purpose=request.purpose,
        input_schema=request.input_schema,
        output_schema=request.output_schema,
        usage_example=request.usage_example,
        required_tools=request.required_tools,
        risk_level=request.risk_level,
        version=request.version,
        created_by_name=request.created_by_name,
        activate=request.activate,
        status=request.status,
    )
    return ItemResponse.model_validate(payload)


@router.post(
    "/generate-with-librarian",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_with_librarian(
    request: LibrarianSkillRequest,
    librarian_service: LibrarianService = Depends(get_librarian_service),
    skill_service: SkillService = Depends(get_skill_service),
) -> ItemResponse:
    """Generate skill using configured librarian provider."""
    generated = librarian_service.generate_candidate_stub(
        provider_id=request.provider_id,
        prompt=request.prompt,
    )
    payload = await skill_service.create_from_librarian_candidate(
        generated=generated,
        category_id=request.category_id,
        tags=request.tags,
        created_by_name=request.created_by_name,
    )
    return ItemResponse.model_validate(payload)


@router.get("", response_model=list[ItemResponse])
async def list_skills(
    item_service: ItemService = Depends(get_item_service),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[ItemResponse]:
    """List all skill items."""
    rows, _ = await item_service.list_items(
        item_type=ItemType.SKILL,
        limit=limit,
        offset=offset,
    )
    return [ItemResponse.model_validate(row) for row in rows]


@router.get("/{item_id}", response_model=ItemResponse)
async def get_skill(
    item_id: str,
    item_service: ItemService = Depends(get_item_service),
) -> ItemResponse:
    """Get one skill."""
    try:
        payload = await item_service.get_item(item_id)
    except LibraryResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    ensure_item_type(
        payload,
        expected=ItemType.SKILL,
        detail="Not a skill item",
    )
    return ItemResponse.model_validate(payload)


@router.patch("/{item_id}", response_model=ItemResponse)
async def patch_skill(
    item_id: str,
    request: SkillPatchRequest,
    skill_service: SkillService = Depends(get_skill_service),
) -> ItemResponse:
    """Patch one skill item."""
    patch_payload = build_patch_payload(request.model_dump())

    try:
        payload = await skill_service.patch_skill(
            item_id=item_id,
            payload=patch_payload,
        )
    except LibraryResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    ensure_item_type(
        payload,
        expected=ItemType.SKILL,
        detail="Not a skill item",
    )
    return ItemResponse.model_validate(payload)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    item_id: str,
    skill_service: SkillService = Depends(get_skill_service),
) -> None:
    """Delete one skill item."""
    try:
        item = await skill_service.item_service.get_item(item_id)
    except LibraryResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    ensure_item_type(
        item,
        expected=ItemType.SKILL,
        detail="Not a skill item",
    )
    await skill_service.item_service.delete_item(item_id)
