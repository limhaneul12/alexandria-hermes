"""Immutable plans and reports for Obsidian index-error repair."""

from __future__ import annotations

from dataclasses import dataclass

from app.obsidian.domain.event_enum.obsidian_enums import ObsidianIndexErrorCode


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianIndexErrorRepairCandidate:
    """One hash-locked Markdown frontmatter repair."""

    note_path: str
    error_code: ObsidianIndexErrorCode
    original_sha256: str
    replacements: tuple[tuple[str, str], ...]
    reason: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianIndexErrorRepairSkip:
    """One index error that requires manual review."""

    note_path: str
    error_code: ObsidianIndexErrorCode
    reason: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianIndexErrorRepairPlan:
    """Dry-run repair plan bound to source hashes."""

    plan_hash: str
    dry_run: bool
    backup_required: bool
    candidates: tuple[ObsidianIndexErrorRepairCandidate, ...]
    skipped: tuple[ObsidianIndexErrorRepairSkip, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianIndexErrorRepairReport:
    """Applied repair evidence with backup and final index status."""

    status: str
    plan_hash: str
    applied_count: int
    backup_root: str
    report_markdown_path: str
    report_json_path: str
    residual_error_notes: int
    residual_error_paths: tuple[str, ...]
