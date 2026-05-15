"""Skill domain payload contracts."""

from __future__ import annotations

from app.library.domain.event_enum.item_enums import ItemStatus
from app.shared.types.extra_types import JSONValue
from typing_extensions import TypedDict


class SkillSchemaPayload(TypedDict, extra_items=JSONValue):
    """Arbitrary JSON schema object owned by a skill contract."""


class SkillDetailsPayload(TypedDict, closed=True):
    """Persistent details object for a skill library item."""

    purpose: str
    input_schema: SkillSchemaPayload
    output_schema: SkillSchemaPayload
    usage_example: str | None
    required_tools: list[str]
    risk_level: str
    version: str
    quality_gate: dict[str, JSONValue]


class SkillCandidateHarnessCheckPayload(TypedDict, closed=True):
    """One deterministic candidate harness check result."""

    name: str
    passed: bool
    message: str


class SkillCandidateHarnessPayload(TypedDict, closed=True):
    """Persistent harness result for an agent-authored skill candidate."""

    status: str
    checks: list[SkillCandidateHarnessCheckPayload]


class AgentSubmittedSkillDetailsPayload(TypedDict, closed=True):
    """Skill details enriched with self-acquisition metadata."""

    purpose: str
    input_schema: SkillSchemaPayload
    output_schema: SkillSchemaPayload
    usage_example: str | None
    required_tools: list[str]
    risk_level: str
    version: str
    evidence_urls: list[str]
    source_summary: str | None
    acquisition_method: str
    harness: SkillCandidateHarnessPayload
    quality_gate: dict[str, JSONValue]


class LibrarianGeneratedSkillDetailsPayload(TypedDict, closed=True):
    """Skill details enriched with librarian generation metadata."""

    purpose: str
    input_schema: SkillSchemaPayload
    output_schema: SkillSchemaPayload
    usage_example: str | None
    required_tools: list[str]
    risk_level: str
    version: str
    librarian_provider_id: str
    prompt: str
    quality_gate: dict[str, JSONValue]


class SkillDetailsPatchPayload(TypedDict, total=False, closed=True):
    """Merged skill details payload for item patch operations."""

    purpose: str
    input_schema: SkillSchemaPayload
    output_schema: SkillSchemaPayload
    usage_example: str | None
    required_tools: list[str]
    risk_level: str
    version: str
    evidence_urls: list[str]
    source_summary: str | None
    acquisition_method: str
    harness: SkillCandidateHarnessPayload
    quality_gate: dict[str, JSONValue]
    librarian_provider_id: str
    prompt: str


class LibrarianSkillItemPayload(TypedDict, closed=True):
    """Normalized item fields from a librarian-generated candidate."""

    title: str
    summary: str
    content: str
    category_id: str | None
    tags: list[str]
    details: LibrarianGeneratedSkillDetailsPayload


class SkillCandidatePayload(TypedDict, closed=True):
    """Item creation fields emitted by skill candidate generation."""

    title: str
    summary: str
    content: str
    purpose: str
    input_schema: SkillSchemaPayload
    output_schema: SkillSchemaPayload
    required_tools: list[str]
    risk_level: str
    version: str
    prompt: str
    provider_id: str


class SkillPatchPayload(TypedDict, total=False, closed=True):
    """Public skill patch payload supported by skill update flows."""

    title: str
    summary: str | None
    content: str
    category_id: str | None
    tags: list[str]
    status: ItemStatus
    purpose: str
    input_schema: SkillSchemaPayload
    output_schema: SkillSchemaPayload
    usage_example: str | None
    required_tools: list[str]
    risk_level: str
    version: str


class SkillItemUpdatePayload(TypedDict, total=False, closed=True):
    """Item-service update payload produced from public skill patch fields."""

    title: str
    summary: str | None
    content: str
    category_id: str | None
    tags: list[str]
    status: ItemStatus
    details: SkillDetailsPatchPayload
