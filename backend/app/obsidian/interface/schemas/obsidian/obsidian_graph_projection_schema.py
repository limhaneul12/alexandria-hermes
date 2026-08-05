"""Pydantic schemas for optional graph projection operations."""

from __future__ import annotations

from typing import Literal

from app.obsidian.application.graph.obsidian_graph_note_diagnostics_service import (
    ObsidianGraphNoteLinkValidationReport,
    ObsidianGraphNoteRebuildReport,
)
from app.obsidian.application.graph.obsidian_graph_projection_rebuild_service import (
    ObsidianGraphProjectionOperationError,
    ObsidianGraphProjectionRebuildReport,
    ObsidianGraphProjectionStatusReport,
)
from app.obsidian.domain.contracts.obsidian_graph_projection_contracts import (
    ObsidianGraphProjectionIssueCount,
)
from pydantic import BaseModel, Field


class ObsidianGraphProjectionOperationErrorResponse(BaseModel):
    """One graph projection operation diagnostic exposed at the API boundary."""

    code: str
    relative_path: str | None = None
    note_id: str | None = None
    edge_id: str | None = None
    detail: str | None = None

    @classmethod
    def from_entity(
        cls,
        error: ObsidianGraphProjectionOperationError,
    ) -> ObsidianGraphProjectionOperationErrorResponse:
        """Build a response error from an internal operation diagnostic.

        Args:
            error: Internal graph projection operation diagnostic.

        Returns:
            API response model for one diagnostic.
        """
        return cls(
            code=error.code,
            relative_path=error.relative_path,
            note_id=error.note_id,
            edge_id=error.edge_id,
            detail=error.detail,
        )


class ObsidianGraphProjectionIssueCountResponse(BaseModel):
    """Counted non-fatal source diagnostic."""

    code: str
    count: int = Field(ge=1)

    @classmethod
    def from_entity(
        cls,
        item: ObsidianGraphProjectionIssueCount,
    ) -> ObsidianGraphProjectionIssueCountResponse:
        return cls(code=item.code.value, count=item.count)


class ObsidianGraphProjectionRebuildResponse(BaseModel):
    """Response body for one explicit graph projection rebuild."""

    status: Literal["completed", "disabled", "failed"]
    graph_read_model: Literal["disabled", "neo4j"]
    run_id: str = Field(min_length=1)
    scanned: int = Field(ge=0)
    indexed: int = Field(ge=0)
    updated: int = Field(ge=0)
    skipped: int = Field(ge=0)
    issue_total: int = Field(ge=0)
    issue_counts: list[ObsidianGraphProjectionIssueCountResponse]
    issues: list[ObsidianGraphProjectionOperationErrorResponse]
    issues_truncated: bool
    errors: list[ObsidianGraphProjectionOperationErrorResponse]
    duration_seconds: float = Field(ge=0)

    @classmethod
    def from_entity(
        cls,
        report: ObsidianGraphProjectionRebuildReport,
    ) -> ObsidianGraphProjectionRebuildResponse:
        """Build a response body from an internal rebuild report.

        Args:
            report: Internal rebuild operation report.

        Returns:
            API response model for the rebuild operation.
        """
        return cls(
            status=report.status,
            graph_read_model=report.graph_read_model,
            run_id=report.run_id,
            scanned=report.scanned,
            indexed=report.indexed,
            updated=report.updated,
            skipped=report.skipped,
            issue_total=report.issue_total,
            issue_counts=[
                ObsidianGraphProjectionIssueCountResponse.from_entity(item)
                for item in report.issue_counts
            ],
            issues=[
                ObsidianGraphProjectionOperationErrorResponse.from_entity(issue)
                for issue in report.issues
            ],
            issues_truncated=report.issues_truncated,
            errors=[
                ObsidianGraphProjectionOperationErrorResponse.from_entity(error)
                for error in report.errors
            ],
            duration_seconds=report.duration_seconds,
        )


class ObsidianGraphProjectionStatusResponse(BaseModel):
    """Response body for graph projection status."""

    status: Literal["disabled", "uninitialized", "ready", "unavailable"]
    graph_read_model: Literal["disabled", "neo4j"]
    enabled: bool
    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    run_id: str | None = None
    projection_version: int | None = Field(default=None, ge=1)
    last_run_issue_total: int = Field(ge=0)
    last_run_issue_counts: list[ObsidianGraphProjectionIssueCountResponse]
    errors: list[ObsidianGraphProjectionOperationErrorResponse]

    @classmethod
    def from_entity(
        cls,
        report: ObsidianGraphProjectionStatusReport,
    ) -> ObsidianGraphProjectionStatusResponse:
        """Build a response body from an internal status report.

        Args:
            report: Internal graph projection status report.

        Returns:
            API response model for graph projection status.
        """
        return cls(
            status=report.status,
            graph_read_model=report.graph_read_model,
            enabled=report.enabled,
            node_count=report.node_count,
            edge_count=report.edge_count,
            run_id=report.run_id,
            projection_version=report.projection_version,
            last_run_issue_total=report.last_run_issue_total,
            last_run_issue_counts=[
                ObsidianGraphProjectionIssueCountResponse.from_entity(item)
                for item in report.last_run_issue_counts
            ],
            errors=[
                ObsidianGraphProjectionOperationErrorResponse.from_entity(error)
                for error in report.errors
            ],
        )


class ObsidianGraphBuildStatusResponse(BaseModel):
    """Response body for graph build/status diagnostics."""

    projection: ObsidianGraphProjectionStatusResponse
    rebuild_note_graph_supported: bool = True
    validation_only_supported: bool = True
    detail: str

    @classmethod
    def from_status_report(
        cls,
        report: ObsidianGraphProjectionStatusReport,
    ) -> ObsidianGraphBuildStatusResponse:
        """Build graph build/status response from the projection status report.

        Args:
            report: Value supplied to from_status_report.

        Returns:
            Result produced by from_status_report.
        """
        return cls(
            projection=ObsidianGraphProjectionStatusResponse.from_entity(report),
            detail=(
                "Per-note rebuild reparses one canonical note into SQLite, replaces "
                "its outgoing edges, then activates a full snapshot projection."
            ),
        )


class ObsidianGraphNoteSelectorResponse(BaseModel):
    """Exact selector echoed by per-note graph diagnostics."""

    note_id: str | None = None
    path: str | None = None


class ObsidianGraphNoteIndexDiagnosticResponse(BaseModel):
    """Indexed-note existence and projection eligibility."""

    exists: bool
    note_id: str | None = None
    relative_path: str | None = None
    title: str | None = None
    index_status: str | None = None
    error_message: str | None = None
    projection_included: bool


class ObsidianGraphResolvedTargetResponse(BaseModel):
    """One outgoing edge resolved to a healthy indexed target."""

    edge_id: str
    target_note_id: str
    target_path: str
    relation: str
    source_kind: str


class ObsidianGraphUnresolvedTargetResponse(BaseModel):
    """One outgoing edge target that cannot be projected cleanly."""

    edge_id: str
    target_path: str
    relation: str
    source_kind: str
    code: str
    detail: str
    target_note_id: str | None = None
    candidate_note_ids: list[str]
    candidate_paths: list[str]


class ObsidianGraphOutgoingLinkDiagnosticResponse(BaseModel):
    """Counts and details for outgoing graph edges from one note."""

    parsed_count: int = Field(ge=0)
    resolved_count: int = Field(ge=0)
    unresolved_count: int = Field(ge=0)
    unresolved_targets: list[ObsidianGraphUnresolvedTargetResponse]
    resolved_targets: list[ObsidianGraphResolvedTargetResponse]


class ObsidianGraphNoteLinkValidationResponse(BaseModel):
    """Response body for per-note graph link validation."""

    selector: ObsidianGraphNoteSelectorResponse
    note: ObsidianGraphNoteIndexDiagnosticResponse
    outgoing: ObsidianGraphOutgoingLinkDiagnosticResponse
    projection: ObsidianGraphProjectionStatusResponse

    @classmethod
    def from_entity(
        cls,
        report: ObsidianGraphNoteLinkValidationReport,
    ) -> ObsidianGraphNoteLinkValidationResponse:
        """Build response body from the internal per-note diagnostics report.

        Args:
            report: Value supplied to from_entity.

        Returns:
            Result produced by from_entity.
        """
        return cls(
            selector=ObsidianGraphNoteSelectorResponse(
                note_id=report.selector.note_id,
                path=report.selector.path,
            ),
            note=ObsidianGraphNoteIndexDiagnosticResponse(
                exists=report.note.exists,
                note_id=report.note.note_id,
                relative_path=report.note.relative_path,
                title=report.note.title,
                index_status=report.note.index_status,
                error_message=report.note.error_message,
                projection_included=report.note.projection_included,
            ),
            outgoing=ObsidianGraphOutgoingLinkDiagnosticResponse(
                parsed_count=report.outgoing.parsed_count,
                resolved_count=report.outgoing.resolved_count,
                unresolved_count=report.outgoing.unresolved_count,
                unresolved_targets=[
                    ObsidianGraphUnresolvedTargetResponse(
                        edge_id=target.edge_id,
                        target_note_id=target.target_note_id,
                        target_path=target.target_path,
                        relation=target.relation,
                        source_kind=target.source_kind,
                        code=target.code,
                        detail=target.detail,
                        candidate_note_ids=list(target.candidate_note_ids),
                        candidate_paths=list(target.candidate_paths),
                    )
                    for target in report.outgoing.unresolved_targets
                ],
                resolved_targets=[
                    ObsidianGraphResolvedTargetResponse(
                        edge_id=target.edge_id,
                        target_note_id=target.target_note_id,
                        target_path=target.target_path,
                        relation=target.relation,
                        source_kind=target.source_kind,
                    )
                    for target in report.outgoing.resolved_targets
                ],
            ),
            projection=ObsidianGraphProjectionStatusResponse.from_entity(
                report.projection_status
            ),
        )


class ObsidianGraphNoteRebuildResponse(BaseModel):
    """Response for focused SQLite edge refresh plus projection activation."""

    replace_existing_edges: bool
    validation: ObsidianGraphNoteLinkValidationResponse
    projection: ObsidianGraphProjectionRebuildResponse

    @classmethod
    def from_entity(
        cls,
        report: ObsidianGraphNoteRebuildReport,
    ) -> ObsidianGraphNoteRebuildResponse:
        """Create a public response from one note graph rebuild report.

        Args:
            report: Value supplied to from_entity.

        Returns:
            Result produced by from_entity.
        """
        return cls(
            replace_existing_edges=report.replace_existing_edges,
            validation=ObsidianGraphNoteLinkValidationResponse.from_entity(
                report.validation
            ),
            projection=ObsidianGraphProjectionRebuildResponse.from_entity(
                report.projection
            ),
        )
