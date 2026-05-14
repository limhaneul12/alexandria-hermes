"""Skill item command contracts."""

from __future__ import annotations

from dataclasses import dataclass

from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.library.domain.types.skill_payload_types import (
    LibrarianGeneratedSkillDetailsPayload,
    SkillDetailsPayload,
    SkillSchemaPayload,
)


@dataclass(frozen=True, kw_only=True)
class SkillItemCreateCommand:
    """Typed arguments for ItemService.create_item."""

    item_type: ItemType
    title: str
    summary: str | None
    content: str
    category_id: str | None
    tags: list[str]
    status: ItemStatus
    source_type: SourceType
    created_by_type: CreatedByType
    created_by_name: str
    details: SkillDetailsPayload | LibrarianGeneratedSkillDetailsPayload


@dataclass(frozen=True, kw_only=True)
class SkillCreateFields:
    """Common public fields used to create a skill item."""

    title: str
    summary: str | None
    content: str
    category_id: str | None
    tags: list[str]
    purpose: str
    input_schema: SkillSchemaPayload
    output_schema: SkillSchemaPayload
    usage_example: str | None
    required_tools: list[str]
    risk_level: str
    version: str
    created_by_name: str
    activate: bool
    status: ItemStatus | None
