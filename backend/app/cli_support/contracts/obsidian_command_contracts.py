"""CLI command contracts for Obsidian integration."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.obsidian.domain.event_enum.obsidian_enums import AlexandriaNoteType


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianSearchCommand:
    """Parameters for Obsidian search."""

    query: str
    limit: int
    alexandria_type: AlexandriaNoteType | None
    project: str | None
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianReadCommand:
    """Parameters for Obsidian note read."""

    note_id: str | None
    path: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianRelatedCommand:
    """Parameters for Obsidian related-note lookup."""

    note_id: str | None
    path: str | None
    limit: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianSaveCommand:
    """Parameters for creating one Obsidian note."""

    title: str
    body_file: str
    alexandria_type: AlexandriaNoteType
    note_id: str | None
    path: str | None
    project: str | None
    status: str
    source: str
    frontmatter_json: str | None
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianCaptureCommand:
    """Parameters for migration-safe canonical artifact capture."""

    title: str
    body_file: str
    alexandria_type: AlexandriaNoteType
    note_id: str | None
    path: str | None
    project: str | None
    status: str
    source: str
    frontmatter_json: str | None
    covered_from: str | None
    covered_to: str | None
    prompt_kind: str | None
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianAskCommand:
    """Parameters for Obsidian librarian ask."""

    query: str
    active_note_path: str | None
    selection: str | None
    project: str | None
    save_transcript: bool
    delegate_to_librarian: bool = False
    provider_id: str | None = None
    profile_id: str | None = None
