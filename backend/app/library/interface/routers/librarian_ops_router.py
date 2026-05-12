"""Librarian runtime operations: recommend/classify/candidate generation."""

from __future__ import annotations

from app.library.application.item_service import ItemService
from app.library.application.librarian_service import LibrarianService
from app.library.domain.entities.enums import ItemType
from app.library.interface.routers.dependencies import (
    get_item_service,
    get_librarian_service,
)
from app.library.interface.schemas._types import StrictSchema
from app.library.interface.schemas.item_schema import (
    ClassificationResponse,
    ItemResponse,
)
from fastapi import APIRouter, Depends
from pydantic import ConfigDict, Field


class RecommendRequest(StrictSchema):
    """Input to recommendation endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"query": "fastapi testing", "item_type": "SKILL", "limit": 5}]
        }
    )

    query: str = Field(min_length=1)
    item_type: ItemType = Field(default=ItemType.SKILL)
    limit: int = Field(default=5, ge=1, le=20)


class ClassifyRequest(StrictSchema):
    """Input to classifier endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"text": "Create a workflow for reviewing generated skills."}]
        }
    )

    text: str = Field(min_length=1)


class CreateCandidateRequest(StrictSchema):
    """Input to create skill candidate endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "provider_id": 1,
                    "prompt": "Create a skill for FastAPI dependency overrides.",
                    "category_id": 2,
                }
            ]
        }
    )

    provider_id: int
    prompt: str = Field(min_length=1)
    category_id: int | None = None


router = APIRouter(prefix="/librarian", tags=["librarian"])


@router.post("/recommend", response_model=list[ItemResponse])
async def recommend(
    request: RecommendRequest,
    item_service: ItemService = Depends(get_item_service),
) -> list[ItemResponse]:
    """Recommend items by query with simple keyword search fallback."""
    items = await item_service.search(query=request.query, item_type=request.item_type)
    return [ItemResponse.model_validate(item) for item in items[: request.limit]]


@router.post("/classify", response_model=ClassificationResponse)
async def classify(request: ClassifyRequest) -> ClassificationResponse:
    """Classify prompt into rough taxonomy categories."""
    lowered = request.text.lower()
    if "workflow" in lowered:
        return ClassificationResponse(label=ItemType.WORKFLOW, confidence=0.76)
    if "api" in lowered or "agent" in lowered:
        return ClassificationResponse(label=ItemType.SKILL, confidence=0.83)
    return ClassificationResponse(label=ItemType.KNOWLEDGE, confidence=0.55)


@router.post("/create-skill-candidate", response_model=ItemResponse)
async def create_skill_candidate(
    request: CreateCandidateRequest,
    librarian_service: LibrarianService = Depends(get_librarian_service),
) -> ItemResponse:
    """Generate candidate payload and return draft candidate."""
    candidate = librarian_service.generate_candidate_stub(
        provider_id=request.provider_id,
        prompt=request.prompt,
    )
    # Keep API shape as draft skill candidate without persistence.
    result = {
        "id": 0,
        "item_type": "SKILL",
        "title": candidate["title"],
        "summary": candidate["summary"],
        "content": candidate["content"],
        "category_id": request.category_id,
        "tags": ["draft", "librarian"],
        "details": {
            "purpose": candidate["purpose"],
            "input_schema": candidate["input_schema"],
            "output_schema": candidate["output_schema"],
            "required_tools": candidate["required_tools"],
            "risk_level": candidate["risk_level"],
            "version": candidate["version"],
        },
        "status": "DRAFT",
        "source_type": "LIBRARIAN_CREATED",
        "created_by_type": "LIBRARIAN",
        "created_by_name": "librarian",
    }
    return ItemResponse.model_validate(result)
