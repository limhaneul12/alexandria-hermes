"""Library CLI command contracts."""

from __future__ import annotations

from dataclasses import dataclass

from app.library.domain.event_enum.item_enums import ItemType
from app.library.domain.event_enum.prompt_enums import PromptKind
from app.library.domain.event_enum.skill_enums import RiskLevel


@dataclass(frozen=True, slots=True, kw_only=True)
class SkillsListCommand:
    """Parameters for listing skills."""

    limit: int
    offset: int


@dataclass(frozen=True, slots=True, kw_only=True)
class SkillsSearchCommand:
    """Parameters for searching skill candidates."""

    query: str
    tool: list[str]
    risk_level: RiskLevel | None
    tag: list[str]
    limit: int
    offset: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ItemIdCommand:
    """Parameters for commands targeting one library item."""

    item_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PromptsListCommand:
    """Parameters for listing prompts."""

    limit: int
    offset: int
    kind: PromptKind | None
    tag: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class PromptsUseCommand:
    """Parameters for rendering and recording prompt usage."""

    item_id: str
    actor_id: str | None
    actor_name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PromptsSearchCommand:
    """Parameters for searching prompt library items."""

    query: str
    limit: int
    offset: int
    kind: PromptKind | None
    tag: list[str]


@dataclass(frozen=True, slots=True, kw_only=True)
class PromptVersionCommand:
    """Parameters for updating a prompt version and optional change summary."""

    item_id: str
    version: str
    change_summary: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class PromptDeprecateCommand:
    """Parameters for deprecating one prompt."""

    item_id: str
    reason: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class PromptDiffCommand:
    """Parameters for diffing two prompt records."""

    left_item_id: str
    right_item_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class FoldersListCommand:
    """Parameters for listing folders."""

    tree: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class FoldersCreateCommand:
    """Parameters for creating a folder."""

    name: str
    parent_id: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class FoldersEnsureCommand:
    """Parameters for ensuring a nested folder path."""

    path: str


@dataclass(frozen=True, slots=True, kw_only=True)
class FolderIdCommand:
    """Parameters for commands targeting one folder."""

    folder_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class LibraryListCommand:
    """Parameters for listing all library items."""

    limit: int
    offset: int
    item_type: ItemType | None
    folder_id: str | None
    query: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class LibrarySearchCommand:
    """Parameters for searching library items."""

    query: str
    limit: int
    offset: int
    item_type: ItemType | None
    content_mode: str
