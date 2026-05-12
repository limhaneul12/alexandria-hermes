"""Workflow request and response schemas."""

from __future__ import annotations

from app.library.domain.entities.enums import ItemStatus
from app.library.interface.schemas._types import StrictSchema
from app.shared.types.extra_types import JSONValue
from pydantic import ConfigDict, Field


class WorkflowCreateRequest(StrictSchema):
    """Payload for workflow registration."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "Review generated skill",
                    "summary": "Human review before activation.",
                    "content": "Check scope, examples, and risk before publishing.",
                    "category_id": 2,
                    "tags": ["review"],
                    "steps": ["Read candidate", "Run examples", "Activate if safe"],
                    "related_skill_ids": [10],
                    "expected_result": "Approved skill is active.",
                    "use_case": "Skill curation",
                    "created_by_name": "alex",
                    "status": "DRAFT",
                }
            ]
        }
    )

    title: str = Field(min_length=1)
    summary: str | None = None
    content: str = Field(min_length=1)
    category_id: int | None = None
    tags: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    related_skill_ids: list[int] = Field(default_factory=list)
    expected_result: str | None = None
    use_case: str | None = None
    created_by_name: str
    status: ItemStatus = ItemStatus.DRAFT


class WorkflowPatchRequest(StrictSchema):
    """Patch payload for workflow updates."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "steps": [
                        "Read candidate",
                        "Run examples",
                        "Update metadata",
                        "Activate if safe",
                    ],
                    "status": "ACTIVE",
                }
            ]
        }
    )

    title: str | None = None
    summary: str | None = None
    content: str | None = None
    category_id: int | None = None
    tags: list[str] | None = None
    status: ItemStatus | None = None
    steps: list[str] | None = None
    related_skill_ids: list[int] | None = None
    expected_result: str | None = None
    use_case: str | None = None


class WorkflowResponse(StrictSchema):
    """Workflow response payload."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 12,
                    "item_type": "WORKFLOW",
                    "title": "Review generated skill",
                    "summary": "Human review before activation.",
                    "content": "Check scope, examples, and risk before publishing.",
                    "category_id": 2,
                    "tags": ["review"],
                    "details": {
                        "steps": ["Read candidate", "Run examples", "Activate if safe"],
                        "related_skill_ids": [10],
                    },
                    "status": "ACTIVE",
                    "source_type": "USER_CREATED",
                    "created_by_type": "USER",
                    "created_by_name": "alex",
                }
            ]
        }
    )

    id: int
    item_type: str
    title: str
    summary: str | None
    content: str
    category_id: int | None
    tags: list[str]
    details: dict[str, JSONValue]
    status: str
    source_type: str
    created_by_type: str
    created_by_name: str
