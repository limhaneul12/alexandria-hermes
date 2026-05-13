"""Schemas for skill-specific endpoints."""

from __future__ import annotations

from app.library.domain.entities.enums import ItemStatus, RiskLevel
from app.library.interface.schemas._types import StrictSchema
from app.shared.types.extra_types import JSONValue
from pydantic import ConfigDict, Field, field_validator


def _item_status(value: object) -> ItemStatus:
    """Accept public JSON item status values at API boundaries."""
    if isinstance(value, ItemStatus):
        return value
    if isinstance(value, str):
        return ItemStatus(value)
    raise ValueError("status must be a valid item status")


def _risk_level(value: object) -> RiskLevel:
    """Accept public JSON risk level values at API boundaries."""
    if isinstance(value, RiskLevel):
        return value
    if isinstance(value, str):
        return RiskLevel(value)
    raise ValueError("risk_level must be a valid risk level")


class SkillCreateRequest(StrictSchema):
    """Payload for direct skill creation."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "FastAPI dependency override",
                    "summary": "Override narrow route dependencies in tests.",
                    "content": "Use app.dependency_overrides with a fake service.",
                    "category_id": "00000000-0000-4000-8000-000000000002",
                    "tags": ["fastapi", "testing"],
                    "purpose": "Test API routes without broad container coupling.",
                    "input_schema": {
                        "type": "object",
                        "properties": {"route": {"type": "string"}},
                    },
                    "output_schema": {
                        "type": "object",
                        "properties": {"status": {"type": "string"}},
                    },
                    "usage_example": "Override get_item_service with a fake ItemService.",
                    "required_tools": ["pytest"],
                    "risk_level": "LOW",
                    "version": "1.0.0",
                    "created_by_name": "alex",
                    "status": "DRAFT",
                }
            ]
        }
    )

    title: str = Field(min_length=1)
    summary: str | None = None
    content: str = Field(min_length=1)
    category_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    purpose: str = Field(min_length=1)
    input_schema: dict[str, JSONValue] = Field(default_factory=dict)
    output_schema: dict[str, JSONValue] = Field(default_factory=dict)
    usage_example: str | None = None
    required_tools: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    version: str = "1.0.0"
    created_by_name: str
    status: ItemStatus = ItemStatus.DRAFT

    @field_validator("risk_level", mode="before")
    @classmethod
    def parse_risk_level(cls, value: object) -> RiskLevel:
        """Parse JSON risk level values."""
        return _risk_level(value)

    @field_validator("status", mode="before")
    @classmethod
    def parse_status(cls, value: object) -> ItemStatus:
        """Parse JSON status values."""
        return _item_status(value)


class AgentSubmitSkillRequest(StrictSchema):
    """Payload from agent-generated or manual structured candidate."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "Agent-authored FastAPI skill",
                    "purpose": "Capture route testing guidance.",
                    "summary": "Generated candidate from an agent.",
                    "content": "Use narrow dependency overrides.",
                    "category_id": "00000000-0000-4000-8000-000000000002",
                    "tags": ["agent", "fastapi"],
                    "input_schema": {},
                    "output_schema": {},
                    "usage_example": "Submit, review, then activate.",
                    "required_tools": ["pytest"],
                    "risk_level": "LOW",
                    "version": "1.0.0",
                    "created_by_name": "research-agent",
                    "activate": False,
                    "status": "DRAFT",
                }
            ]
        }
    )

    title: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    summary: str | None = None
    content: str = Field(min_length=1)
    category_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    input_schema: dict[str, JSONValue] = Field(default_factory=dict)
    output_schema: dict[str, JSONValue] = Field(default_factory=dict)
    usage_example: str | None = None
    required_tools: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    version: str = "1.0.0"
    created_by_name: str
    activate: bool = False
    status: ItemStatus = ItemStatus.DRAFT

    @field_validator("risk_level", mode="before")
    @classmethod
    def parse_risk_level(cls, value: object) -> RiskLevel:
        """Parse JSON risk level values."""
        return _risk_level(value)

    @field_validator("status", mode="before")
    @classmethod
    def parse_status(cls, value: object) -> ItemStatus:
        """Parse JSON status values."""
        return _item_status(value)


class SkillPatchRequest(StrictSchema):
    """Patch payload for editing an existing skill."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Updated route testing guidance.",
                    "status": "ACTIVE",
                    "required_tools": ["pytest", "httpx"],
                    "version": "1.0.1",
                }
            ]
        }
    )

    title: str | None = None
    summary: str | None = None
    content: str | None = None
    category_id: str | None = None
    tags: list[str] | None = None
    status: ItemStatus | None = None
    purpose: str | None = None
    input_schema: dict[str, JSONValue] | None = None
    output_schema: dict[str, JSONValue] | None = None
    usage_example: str | None = None
    required_tools: list[str] | None = None
    risk_level: RiskLevel | None = None
    version: str | None = None

    @field_validator("risk_level", mode="before")
    @classmethod
    def parse_risk_level(cls, value: object) -> RiskLevel | None:
        """Parse JSON risk level values when provided."""
        if value is None:
            return None
        return _risk_level(value)

    @field_validator("status", mode="before")
    @classmethod
    def parse_status(cls, value: object) -> ItemStatus | None:
        """Parse JSON status values when provided."""
        if value is None:
            return None
        return _item_status(value)


class LibrarianSkillRequest(StrictSchema):
    """Payload to generate candidate through librarian provider."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "provider_id": "00000000-0000-4000-8000-000000000456",
                    "prompt": "Create a skill for FastAPI dependency overrides.",
                    "category_id": "00000000-0000-4000-8000-000000000002",
                    "tags": ["fastapi"],
                    "created_by_name": "alex",
                }
            ]
        }
    )

    provider_id: str
    prompt: str = Field(min_length=1)
    category_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_by_name: str


class SkillResponse(StrictSchema):
    """Skill payload with normalized type fields."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "00000000-0000-4000-8000-000000000010",
                    "item_type": "SKILL",
                    "title": "FastAPI dependency override",
                    "summary": "Override narrow route dependencies in tests.",
                    "content": "Use app.dependency_overrides with a fake service.",
                    "details": {
                        "purpose": "Test API routes without broad container coupling.",
                        "risk_level": "LOW",
                    },
                    "category_id": "00000000-0000-4000-8000-000000000002",
                    "status": "ACTIVE",
                    "source_type": "USER_CREATED",
                    "created_by_type": "USER",
                    "created_by_name": "alex",
                }
            ]
        }
    )

    id: str
    item_type: str
    title: str
    summary: str | None
    content: str
    details: dict[str, JSONValue]
    category_id: str | None
    status: str
    source_type: str
    created_by_type: str
    created_by_name: str
