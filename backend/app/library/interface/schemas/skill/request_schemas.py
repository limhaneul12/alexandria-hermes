"""Request schemas for skill-specific endpoints."""

from __future__ import annotations

from app.library.domain.event_enum.item_enums import ItemStatus
from app.library.domain.event_enum.skill_enums import RiskLevel
from app.library.interface.schemas.skill.examples import (
    AGENT_SUBMIT_SKILL_EXAMPLE,
    LIBRARIAN_SKILL_EXAMPLE,
    SKILL_CREATE_EXAMPLE,
    SKILL_PATCH_EXAMPLE,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.types.extra_types import JSONValue
from pydantic import ConfigDict, Field


class SkillCreateRequest(StrictSchemaModel):
    """Payload for direct skill creation."""

    model_config = ConfigDict(json_schema_extra={"examples": [SKILL_CREATE_EXAMPLE]})

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


class AgentSubmitSkillRequest(StrictSchemaModel):
    """Payload from agent-generated or manual structured candidate."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [AGENT_SUBMIT_SKILL_EXAMPLE]}
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
    evidence_urls: list[str] = Field(default_factory=list)
    source_summary: str | None = None


class SkillPatchRequest(StrictSchemaModel):
    """Patch payload for editing an existing skill."""

    model_config = ConfigDict(json_schema_extra={"examples": [SKILL_PATCH_EXAMPLE]})

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


class LibrarianSkillRequest(StrictSchemaModel):
    """Payload to generate candidate through librarian provider."""

    model_config = ConfigDict(json_schema_extra={"examples": [LIBRARIAN_SKILL_EXAMPLE]})

    provider_id: str
    prompt: str = Field(min_length=1)
    category_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_by_name: str
