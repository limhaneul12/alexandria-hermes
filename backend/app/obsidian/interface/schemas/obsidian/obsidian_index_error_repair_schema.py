"""HTTP contracts for backup-first Obsidian index-error repair."""

from __future__ import annotations

from app.obsidian.domain.entities.obsidian_index_error_repair import (
    ObsidianIndexErrorRepairCandidate,
    ObsidianIndexErrorRepairPlan,
    ObsidianIndexErrorRepairReport,
    ObsidianIndexErrorRepairSkip,
)
from app.obsidian.domain.event_enum.obsidian_enums import ObsidianIndexErrorCode
from app.shared.schemas.common_schemas import StrictSchemaModel
from pydantic import Field


class ObsidianIndexErrorRepairCandidateResponse(StrictSchemaModel):
    """One planned source-hash-bound frontmatter repair."""

    note_path: str
    error_code: ObsidianIndexErrorCode
    original_sha256: str
    replacements: dict[str, str]
    reason: str

    @classmethod
    def from_entity(
        cls,
        item: ObsidianIndexErrorRepairCandidate,
    ) -> ObsidianIndexErrorRepairCandidateResponse:
        return cls(
            note_path=item.note_path,
            error_code=item.error_code,
            original_sha256=item.original_sha256,
            replacements=dict(item.replacements),
            reason=item.reason,
        )


class ObsidianIndexErrorRepairSkipResponse(StrictSchemaModel):
    """One index error requiring manual review."""

    note_path: str
    error_code: ObsidianIndexErrorCode
    reason: str

    @classmethod
    def from_entity(
        cls,
        item: ObsidianIndexErrorRepairSkip,
    ) -> ObsidianIndexErrorRepairSkipResponse:
        return cls(
            note_path=item.note_path,
            error_code=item.error_code,
            reason=item.reason,
        )


class ObsidianIndexErrorRepairPlanResponse(StrictSchemaModel):
    """Dry-run plan which must remain unchanged before apply."""

    plan_hash: str
    dry_run: bool
    backup_required: bool
    candidates: list[ObsidianIndexErrorRepairCandidateResponse]
    skipped: list[ObsidianIndexErrorRepairSkipResponse]

    @classmethod
    def from_entity(
        cls,
        plan: ObsidianIndexErrorRepairPlan,
    ) -> ObsidianIndexErrorRepairPlanResponse:
        return cls(
            plan_hash=plan.plan_hash,
            dry_run=plan.dry_run,
            backup_required=plan.backup_required,
            candidates=[
                ObsidianIndexErrorRepairCandidateResponse.from_entity(item)
                for item in plan.candidates
            ],
            skipped=[
                ObsidianIndexErrorRepairSkipResponse.from_entity(item)
                for item in plan.skipped
            ],
        )


class ObsidianIndexErrorRepairApplyRequest(StrictSchemaModel):
    """Hash-lock required to apply the most recently inspected source state."""

    expected_plan_hash: str = Field(min_length=64, max_length=64)


class ObsidianIndexErrorRepairReportResponse(StrictSchemaModel):
    """Evidence for one applied, backup-first repair."""

    status: str
    plan_hash: str
    applied_count: int
    backup_root: str
    report_markdown_path: str
    report_json_path: str
    residual_error_notes: int
    residual_error_paths: list[str]

    @classmethod
    def from_entity(
        cls,
        report: ObsidianIndexErrorRepairReport,
    ) -> ObsidianIndexErrorRepairReportResponse:
        return cls(
            status=report.status,
            plan_hash=report.plan_hash,
            applied_count=report.applied_count,
            backup_root=report.backup_root,
            report_markdown_path=report.report_markdown_path,
            report_json_path=report.report_json_path,
            residual_error_notes=report.residual_error_notes,
            residual_error_paths=list(report.residual_error_paths),
        )
