"""Pydantic schemas for optional graph projection operations."""

from __future__ import annotations

from typing import Literal

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
