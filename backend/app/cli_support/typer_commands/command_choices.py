"""Native Typer command choices backed by domain enums."""

from __future__ import annotations

from enum import StrEnum

from app.library.domain.event_enum.item_enums import (
    CreatedByType as PromptCreatorType,
    ItemType as LibraryItemType,
    SourceType as PromptSourceType,
)
from app.library.domain.event_enum.prompt_enums import (
    PromptContentFormat,
    PromptDomain,
    PromptKind,
    PromptTaskType,
)
from app.library.domain.event_enum.skill_enums import RiskLevel as SkillRiskLevel

__all__ = [
    "LibraryItemType",
    "PromptContentFormat",
    "PromptCreatorType",
    "PromptDomain",
    "PromptKind",
    "PromptSourceType",
    "PromptTaskType",
    "SetupRuntimeMode",
    "SkillRiskLevel",
]


class SetupRuntimeMode(StrEnum):
    """Supported Alexandria-Hermes runtime setup modes."""

    FULLSTACK_COMPOSE = "fullstack-compose"
    FULLSTACK_SEPARATE = "fullstack-separate"
    BACKEND_DAEMON = "backend-daemon"
    GUIDEBOOK_ONLY = "guidebook-only"
