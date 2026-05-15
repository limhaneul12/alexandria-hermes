"""Request schemas for skill-specific endpoints."""

from __future__ import annotations

from app.library.domain.event_enum.item_enums import ItemStatus
from app.library.domain.event_enum.skill_enums import RiskLevel
from app.library.interface.schemas._types import StrictSchema
from app.library.interface.schemas.skill.enum_parsing import item_status, risk_level
from app.library.interface.schemas.skill.examples import (
    AGENT_SUBMIT_SKILL_EXAMPLE,
    LIBRARIAN_SKILL_EXAMPLE,
    SKILL_CREATE_EXAMPLE,
    SKILL_PATCH_EXAMPLE,
)
from app.shared.types.extra_types import JSONValue
from pydantic import ConfigDict, Field, field_validator


class SkillCreateRequest(StrictSchema):
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

    @field_validator("risk_level", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_risk_level(cls, value: object) -> RiskLevel:
        """Parse JSON risk level values.

        Args:
            value [object]: Value supplied to parse_risk_level.

        Returns:
            RiskLevel: Value produced by parse_risk_level.
        """
        parsed_level = risk_level(value)
        return parsed_level

    @field_validator("status", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_status(cls, value: object) -> ItemStatus:
        """Parse JSON status values.

        Args:
            value [object]: Value supplied to parse_status.

        Returns:
            ItemStatus: Value produced by parse_status.
        """
        parsed_status = item_status(value)
        return parsed_status


class AgentSubmitSkillRequest(StrictSchema):
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

    @field_validator("risk_level", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_risk_level(cls, value: object) -> RiskLevel:
        """Parse JSON risk level values.

        Args:
            value [object]: Value supplied to parse_risk_level.

        Returns:
            RiskLevel: Value produced by parse_risk_level.
        """
        parsed_level = risk_level(value)
        return parsed_level

    @field_validator("status", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_status(cls, value: object) -> ItemStatus:
        """Parse JSON status values.

        Args:
            value [object]: Value supplied to parse_status.

        Returns:
            ItemStatus: Value produced by parse_status.
        """
        parsed_status = item_status(value)
        return parsed_status


class SkillPatchRequest(StrictSchema):
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

    @field_validator("risk_level", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_risk_level(cls, value: object) -> RiskLevel | None:
        """Parse JSON risk level values when provided.

        Args:
            value [object]: Value supplied to parse_risk_level.

        Returns:
            RiskLevel | None: Value produced by parse_risk_level.
        """
        if value is None:
            parsed_level = None
        else:
            parsed_level = risk_level(value)
        return parsed_level

    @field_validator("status", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_status(cls, value: object) -> ItemStatus | None:
        """Parse JSON status values when provided.

        Args:
            value [object]: Value supplied to parse_status.

        Returns:
            ItemStatus | None: Value produced by parse_status.
        """
        if value is None:
            parsed_status = None
        else:
            parsed_status = item_status(value)
        return parsed_status


class LibrarianSkillRequest(StrictSchema):
    """Payload to generate candidate through librarian provider."""

    model_config = ConfigDict(json_schema_extra={"examples": [LIBRARIAN_SKILL_EXAMPLE]})

    provider_id: str
    prompt: str = Field(min_length=1)
    category_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_by_name: str
