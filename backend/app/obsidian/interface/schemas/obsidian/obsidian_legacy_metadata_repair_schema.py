"""HTTP contracts for dry-run-first legacy metadata repair."""

from __future__ import annotations

from app.obsidian.domain.entities.obsidian_legacy_metadata_repair import (
    ObsidianLegacyMetadataRepairCandidate,
    ObsidianLegacyMetadataRepairFinding,
    ObsidianLegacyMetadataRepairPlan,
    ObsidianLegacyMetadataRepairReport,
    ObsidianLegacyMetadataRepairResult,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from pydantic import Field


class ObsidianLegacyMetadataRepairFindingResponse(StrictSchemaModel):
    """One current and proposed legacy metadata value."""

    field_name: str
    current_value: str
    proposed_value: list[str] | bool | None
    reason: str
    is_repairable: bool

    @classmethod
    def from_entity(
        cls,
        finding: ObsidianLegacyMetadataRepairFinding,
    ) -> ObsidianLegacyMetadataRepairFindingResponse:
        proposed = finding.proposed_value
        return cls(
            field_name=finding.field_name,
            current_value=finding.current_value,
            proposed_value=list(proposed) if isinstance(proposed, tuple) else proposed,
            reason=finding.reason,
            is_repairable=finding.is_repairable,
        )


class ObsidianLegacyMetadataRepairCandidateResponse(StrictSchemaModel):
    """One affected Markdown path bound to its current content hash."""

    note_path: str
    original_sha256: str
    findings: list[ObsidianLegacyMetadataRepairFindingResponse]

    @classmethod
    def from_entity(
        cls,
        candidate: ObsidianLegacyMetadataRepairCandidate,
    ) -> ObsidianLegacyMetadataRepairCandidateResponse:
        return cls(
            note_path=candidate.note_path,
            original_sha256=candidate.original_sha256,
            findings=[
                ObsidianLegacyMetadataRepairFindingResponse.from_entity(finding)
                for finding in candidate.findings
            ],
        )


class ObsidianLegacyMetadataRepairPlanResponse(StrictSchemaModel):
    """Non-mutating scan report and hash lock for explicit apply."""

    plan_hash: str
    dry_run: bool
    backup_required: bool
    scanned_documents: int
    affected_documents: int
    repairable_fields: int
    manual_review_fields: int
    unrecoverable_redacted_urls: int
    candidates: list[ObsidianLegacyMetadataRepairCandidateResponse]

    @classmethod
    def from_entity(
        cls,
        plan: ObsidianLegacyMetadataRepairPlan,
    ) -> ObsidianLegacyMetadataRepairPlanResponse:
        return cls(
            plan_hash=plan.plan_hash,
            dry_run=plan.dry_run,
            backup_required=plan.backup_required,
            scanned_documents=plan.scanned_documents,
            affected_documents=plan.affected_documents,
            repairable_fields=plan.repairable_fields,
            manual_review_fields=plan.manual_review_fields,
            unrecoverable_redacted_urls=plan.unrecoverable_redacted_urls,
            candidates=[
                ObsidianLegacyMetadataRepairCandidateResponse.from_entity(candidate)
                for candidate in plan.candidates
            ],
        )


class ObsidianLegacyMetadataRepairApplyRequest(StrictSchemaModel):
    """Explicit acceptance of the inspected plan hash."""

    expected_plan_hash: str = Field(min_length=64, max_length=64)


class ObsidianLegacyMetadataRepairResultResponse(StrictSchemaModel):
    """Before/after hash evidence for one attempted document."""

    note_path: str
    before_sha256: str
    after_sha256: str
    success: bool
    failure_reason: str | None

    @classmethod
    def from_entity(
        cls,
        result: ObsidianLegacyMetadataRepairResult,
    ) -> ObsidianLegacyMetadataRepairResultResponse:
        return cls(
            note_path=result.note_path,
            before_sha256=result.before_sha256,
            after_sha256=result.after_sha256,
            success=result.success,
            failure_reason=result.failure_reason,
        )


class ObsidianLegacyMetadataRepairReportResponse(StrictSchemaModel):
    """Applied repair evidence with verified backup location."""

    status: str
    plan_hash: str
    backup_root: str
    applied_count: int
    failed_count: int
    unrecoverable_redacted_urls: int
    results: list[ObsidianLegacyMetadataRepairResultResponse]

    @classmethod
    def from_entity(
        cls,
        report: ObsidianLegacyMetadataRepairReport,
    ) -> ObsidianLegacyMetadataRepairReportResponse:
        return cls(
            status=report.status,
            plan_hash=report.plan_hash,
            backup_root=report.backup_root,
            applied_count=report.applied_count,
            failed_count=report.failed_count,
            unrecoverable_redacted_urls=report.unrecoverable_redacted_urls,
            results=[
                ObsidianLegacyMetadataRepairResultResponse.from_entity(result)
                for result in report.results
            ],
        )
