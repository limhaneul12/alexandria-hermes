"""Immutable plans and reports for legacy Obsidian metadata repair."""

from __future__ import annotations

from dataclasses import dataclass

type LegacyMetadataValue = tuple[str, ...] | bool | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianLegacyMetadataRepairFinding:
    """One legacy field value and its type-preserving replacement."""

    field_name: str
    current_value: str
    proposed_value: LegacyMetadataValue
    reason: str
    is_repairable: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianLegacyMetadataRepairCandidate:
    """One source-hash-bound Markdown metadata repair."""

    note_path: str
    original_sha256: str
    findings: tuple[ObsidianLegacyMetadataRepairFinding, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianLegacyMetadataRepairPlan:
    """Dry-run plan for all managed legacy metadata."""

    plan_hash: str
    dry_run: bool
    backup_required: bool
    scanned_documents: int
    affected_documents: int
    repairable_fields: int
    manual_review_fields: int
    unrecoverable_redacted_urls: int
    candidates: tuple[ObsidianLegacyMetadataRepairCandidate, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianLegacyMetadataRepairResult:
    """Before/after evidence for one attempted Markdown repair."""

    note_path: str
    before_sha256: str
    after_sha256: str
    success: bool
    failure_reason: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianLegacyMetadataRepairReport:
    """Backup and content-hash evidence for an explicit apply."""

    status: str
    plan_hash: str
    backup_root: str
    applied_count: int
    failed_count: int
    unrecoverable_redacted_urls: int
    results: tuple[ObsidianLegacyMetadataRepairResult, ...]
