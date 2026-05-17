"""Internal query DTOs for library candidate search."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.library.domain.event_enum.prompt_enums import PromptKind
from app.library.domain.event_enum.search_enums import LibrarySearchField
from app.library.domain.event_enum.skill_enums import RiskLevel


@dataclass(frozen=True, slots=True)
class ItemSearchQuery:
    """Normalized internal search options for candidate discovery."""

    query: str | None = None
    item_types: tuple[ItemType, ...] = field(default_factory=tuple)
    category_id: str | None = None
    include_descendant_categories: bool = False
    tags_any: tuple[str, ...] = field(default_factory=tuple)
    tags_all: tuple[str, ...] = field(default_factory=tuple)
    status: ItemStatus | None = None
    prompt_kind: PromptKind | None = None
    risk_level: RiskLevel | None = None
    required_tools: tuple[str, ...] = field(default_factory=tuple)
    source_type: SourceType | None = None
    created_by_type: CreatedByType | None = None
    created_by_name: str | None = None
    updated_since: datetime | None = None
    updated_before: datetime | None = None
    search_fields: tuple[LibrarySearchField, ...] = field(default_factory=tuple)
    limit: int = 20
    offset: int = 0
