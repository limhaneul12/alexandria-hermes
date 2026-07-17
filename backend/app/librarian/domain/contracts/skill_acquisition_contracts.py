"""Durable skill-acquisition job command contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.librarian.domain.event_enum.collaboration_enums import (
    SkillAcquisitionJobStage,
    SkillAcquisitionJobStatus,
)
from app.librarian.domain.event_enum.skill_acquisition_enums import (
    ItemStatus,
    RiskLevel,
)
from app.librarian.domain.types.skill_acquisition_payload_types import (
    SkillSchemaPayload,
)
from app.shared.types.extra_types import JSONObject


def _empty_skill_schema() -> SkillSchemaPayload:
    return {}


@dataclass(frozen=True, slots=True, kw_only=True)
class SkillAcquisitionJobCreate:
    """Fields required to create one durable skill-acquisition job."""

    id: str
    prompt: str
    agent_name: str
    project: str | None
    task_summary: str | None
    status: SkillAcquisitionJobStatus
    provider_id: str | None
    librarian_profile_id: str | None
    result_summary: str | None
    evidence_urls: list[str] = field(default_factory=list)
    error_message: str | None = None
    skill_id: str | None = None
    context_id: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    stage: SkillAcquisitionJobStage | None = None
    progress_summary: str | None = None
    skill_note_path: str | None = None
    reindex_status: str | None = None
    verification_status: str | None = None
    handoff: JSONObject | None = None
    repair_hint: str | None = None
    search_snapshot: JSONObject | None = None
    acquisition_override_reason: str | None = None
    prompt_reference: str | None = None
    prompt_reference_hash: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SkillAcquisitionJobUpdate:
    """Fields allowed when updating one durable skill-acquisition job."""

    status: SkillAcquisitionJobStatus
    result_summary: str | None = None
    evidence_urls: list[str] = field(default_factory=list)
    error_message: str | None = None
    skill_id: str | None = None
    context_id: str | None = None
    updated_at: datetime
    completed_at: datetime | None = None
    stage: SkillAcquisitionJobStage | None = None
    progress_summary: str | None = None
    skill_note_path: str | None = None
    reindex_status: str | None = None
    verification_status: str | None = None
    handoff: JSONObject | None = None
    repair_hint: str | None = None
    search_snapshot: JSONObject | None = None
    acquisition_override_reason: str | None = None
    prompt_reference: str | None = None
    prompt_reference_hash: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SkillAcquisitionEvidenceItem:
    """Claim-linked source evidence for an acquired skill artifact."""

    url_or_path: str
    title: str | None = None
    source_kind: str | None = None
    publisher_or_repository: str | None = None
    accessed_at: str | None = None
    supports_claims: list[str] = field(default_factory=list)
    freshness: str | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SkillAcquisitionArtifact:
    """Structured skill artifact produced by librarian or agent acquisition."""

    title: str
    purpose: str
    content: str
    summary: str | None = None
    category_id: str | None = None
    tags: list[str] = field(default_factory=list)
    input_schema: SkillSchemaPayload = field(default_factory=_empty_skill_schema)
    output_schema: SkillSchemaPayload = field(default_factory=_empty_skill_schema)
    usage_example: str | None = None
    required_tools: list[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    version: str = "1.0.0"
    created_by_name: str | None = None
    activate: bool = False
    status: ItemStatus = ItemStatus.DRAFT
    evidence_urls: list[str] = field(default_factory=list)
    evidence_items: list[SkillAcquisitionEvidenceItem] = field(default_factory=list)
    source_summary: str | None = None
    next_steps: list[str] = field(default_factory=list)
