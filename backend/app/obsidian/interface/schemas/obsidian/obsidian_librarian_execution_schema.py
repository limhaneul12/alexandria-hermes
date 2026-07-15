"""HTTP schemas for Obsidian librarian execution operations."""

from __future__ import annotations

from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianLibrarianReviewApplyRequest,
    ObsidianLibrarianReviewQueueRequest,
    ObsidianVaultInventoryRequest,
    ObsidianVaultMoveApplyRequest,
    ObsidianVaultMovePlanRequest,
    ObsidianVaultMoveRequest,
)
from app.obsidian.domain.entities.obsidian_note import (
    ObsidianLibrarianJob,
    ObsidianLibrarianReviewQueueItem,
    ObsidianVaultInventoryItem,
    ObsidianVaultMoveApplied,
    ObsidianVaultMoveCandidate,
    ObsidianVaultMovePlan,
    ObsidianVaultMoveReport,
    ObsidianVaultMoveSkip,
)
from app.obsidian.domain.event_enum.obsidian_enums import (
    AlexandriaNoteType,
    ObsidianLibrarianJobStatus,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.schemas.datetime_schemas import AwareTimestamp
from pydantic import Field


class ObsidianVaultInventoryRequestSchema(StrictSchemaModel):
    """Request to inventory managed Obsidian notes under one scope."""

    scope_path: str | None = None

    def to_command(self) -> ObsidianVaultInventoryRequest:
        """Convert request into application command.

        Returns:
            Application inventory request.
        """
        return ObsidianVaultInventoryRequest(scope_path=self.scope_path)


class ObsidianVaultInventoryItemResponse(StrictSchemaModel):
    """One managed note inventory item."""

    id: str
    path: str
    alexandria_type: AlexandriaNoteType
    title: str
    status: str
    tags: list[str]
    project: str | None
    size_bytes: int
    modified_at: AwareTimestamp

    @classmethod
    def from_entity(
        cls,
        item: ObsidianVaultInventoryItem,
    ) -> ObsidianVaultInventoryItemResponse:
        """Create response from inventory item.

        Args:
            item: Inventory item entity.

        Returns:
            HTTP inventory item.
        """
        return cls(
            id=item.note_id,
            path=item.relative_path,
            alexandria_type=item.alexandria_type,
            title=item.title,
            status=item.status,
            tags=item.tags,
            project=item.project,
            size_bytes=item.size_bytes,
            modified_at=item.modified_at,
        )


class ObsidianVaultInventoryResponse(StrictSchemaModel):
    """Inventory response."""

    items: list[ObsidianVaultInventoryItemResponse]
    total: int


class ObsidianLibrarianReviewQueueRequestSchema(StrictSchemaModel):
    """Request for librarian curation candidates."""

    scope_path: str | None = None
    project: str | None = None
    limit: int = Field(default=50, ge=1, le=200)

    def to_command(self) -> ObsidianLibrarianReviewQueueRequest:
        """Convert request into application command.

        Returns:
            Application review queue request.
        """
        return ObsidianLibrarianReviewQueueRequest(
            scope_path=self.scope_path,
            project=self.project,
            limit=self.limit,
        )


class ObsidianLibrarianReviewQueueItemResponse(StrictSchemaModel):
    """One librarian curation queue item."""

    id: str
    path: str
    alexandria_type: AlexandriaNoteType
    title: str
    status: str
    tags: list[str]
    project: str | None
    reason: str
    recommended_action: str
    suggested_destination_path: str | None
    priority: int
    confidence: float
    requires_human_review: bool
    verification_query: str | None

    @classmethod
    def from_entity(
        cls,
        item: ObsidianLibrarianReviewQueueItem,
    ) -> ObsidianLibrarianReviewQueueItemResponse:
        """Create response from curation queue item.

        Args:
            item: Queue item entity.

        Returns:
            Queue item response.
        """
        return cls(
            id=item.note_id,
            path=item.relative_path,
            alexandria_type=item.alexandria_type,
            title=item.title,
            status=item.status,
            tags=item.tags,
            project=item.project,
            reason=item.reason,
            recommended_action=item.recommended_action,
            suggested_destination_path=item.suggested_destination_path,
            priority=item.priority,
            confidence=item.confidence,
            requires_human_review=item.requires_human_review,
            verification_query=item.verification_query,
        )


class ObsidianLibrarianReviewQueueResponse(StrictSchemaModel):
    """Librarian curation queue response."""

    items: list[ObsidianLibrarianReviewQueueItemResponse]
    total: int


class ObsidianLibrarianReviewApplyRequestSchema(StrictSchemaModel):
    """Request to safely apply librarian review queue moves."""

    scope_path: str | None = None
    project: str | None = None
    limit: int = Field(default=50, ge=1, le=200)
    report_path: str | None = None
    reindex: bool = True
    verification_query: str | None = None

    def to_command(self) -> ObsidianLibrarianReviewApplyRequest:
        """Convert request into application command.

        Returns:
            Application review apply request.
        """
        return ObsidianLibrarianReviewApplyRequest(
            scope_path=self.scope_path,
            project=self.project,
            limit=self.limit,
            report_path=self.report_path,
            reindex=self.reindex,
            verification_query=self.verification_query,
        )


class ObsidianVaultPathSearchRequest(StrictSchemaModel):
    """Metadata/path search request for vault operation planning."""

    query: str = Field(min_length=1)
    scope_path: str | None = None


class ObsidianVaultMoveRequestSchema(StrictSchemaModel):
    """One requested safe vault move."""

    source_path: str = Field(min_length=1)
    destination_path: str = Field(min_length=1)
    reason: str = Field(min_length=1)

    def to_command(self) -> ObsidianVaultMoveRequest:
        """Convert request into move command.

        Returns:
            Application move request.
        """
        return ObsidianVaultMoveRequest(
            source_path=self.source_path,
            destination_path=self.destination_path,
            reason=self.reason,
        )


class ObsidianVaultMovePlanRequestSchema(StrictSchemaModel):
    """Dry-run move plan request."""

    moves: list[ObsidianVaultMoveRequestSchema] = Field(min_length=1)

    def to_command(self) -> ObsidianVaultMovePlanRequest:
        """Convert request into application plan command.

        Returns:
            Move plan request.
        """
        return ObsidianVaultMovePlanRequest(
            moves=[move.to_command() for move in self.moves]
        )


class ObsidianVaultMoveApplyRequestSchema(StrictSchemaModel):
    """Safe move application request."""

    moves: list[ObsidianVaultMoveRequestSchema] = Field(min_length=1)
    report_path: str | None = None
    reindex: bool = True
    verification_query: str | None = None

    def to_command(self) -> ObsidianVaultMoveApplyRequest:
        """Convert request into application apply command.

        Returns:
            Move apply request.
        """
        return ObsidianVaultMoveApplyRequest(
            moves=[move.to_command() for move in self.moves],
            report_path=self.report_path,
            reindex=self.reindex,
            verification_query=self.verification_query,
        )


class ObsidianVaultMoveCandidateResponse(StrictSchemaModel):
    """One safety-approved move candidate."""

    source_path: str
    destination_path: str
    reason: str

    @classmethod
    def from_entity(
        cls,
        item: ObsidianVaultMoveCandidate,
    ) -> ObsidianVaultMoveCandidateResponse:
        """Create response from move candidate.

        Args:
            item: Move candidate entity.

        Returns:
            Move candidate response.
        """
        return cls(
            source_path=item.source_path,
            destination_path=item.destination_path,
            reason=item.reason,
        )


class ObsidianVaultMoveSkipResponse(StrictSchemaModel):
    """One skipped move candidate with reason."""

    source_path: str
    destination_path: str
    reason: str

    @classmethod
    def from_entity(cls, item: ObsidianVaultMoveSkip) -> ObsidianVaultMoveSkipResponse:
        """Create response from skipped move.

        Args:
            item: Move skip entity.

        Returns:
            Move skip response.
        """
        return cls(
            source_path=item.source_path,
            destination_path=item.destination_path,
            reason=item.reason,
        )


class ObsidianVaultMovePlanResponse(StrictSchemaModel):
    """Dry-run move plan response."""

    status: str
    hard_delete_performed: bool
    moves: list[ObsidianVaultMoveCandidateResponse]
    skipped: list[ObsidianVaultMoveSkipResponse]
    ambiguous: list[ObsidianVaultMoveSkipResponse]

    @classmethod
    def from_entity(cls, plan: ObsidianVaultMovePlan) -> ObsidianVaultMovePlanResponse:
        """Create response from move plan.

        Args:
            plan: Move plan entity.

        Returns:
            Move plan response.
        """
        return cls(
            status=plan.status,
            hard_delete_performed=plan.hard_delete_performed,
            moves=[
                ObsidianVaultMoveCandidateResponse.from_entity(item)
                for item in plan.moves
            ],
            skipped=[
                ObsidianVaultMoveSkipResponse.from_entity(item) for item in plan.skipped
            ],
            ambiguous=[
                ObsidianVaultMoveSkipResponse.from_entity(item)
                for item in plan.ambiguous
            ],
        )


class ObsidianVaultMoveAppliedResponse(StrictSchemaModel):
    """One applied safe move."""

    source_path: str
    destination_path: str
    reason: str

    @classmethod
    def from_entity(
        cls,
        item: ObsidianVaultMoveApplied,
    ) -> ObsidianVaultMoveAppliedResponse:
        """Create response from applied move.

        Args:
            item: Applied move entity.

        Returns:
            Applied move response.
        """
        return cls(
            source_path=item.source_path,
            destination_path=item.destination_path,
            reason=item.reason,
        )


class ObsidianVaultMoveVerificationResponse(StrictSchemaModel):
    """Verification summary after move application."""

    source_root_loose_notes_remaining: int
    reindex_status: str
    verification_hits: int


class ObsidianVaultMoveReportResponse(StrictSchemaModel):
    """Safe move application report response."""

    status: str
    hard_delete_performed: bool
    moved: list[ObsidianVaultMoveAppliedResponse]
    skipped: list[ObsidianVaultMoveSkipResponse]
    ambiguous: list[ObsidianVaultMoveSkipResponse]
    verification: ObsidianVaultMoveVerificationResponse
    report_markdown_path: str
    report_json_path: str

    @classmethod
    def from_entity(
        cls,
        report: ObsidianVaultMoveReport,
    ) -> ObsidianVaultMoveReportResponse:
        """Create response from move report.

        Args:
            report: Move report entity.

        Returns:
            Move report response.
        """
        return cls(
            status=report.status,
            hard_delete_performed=report.hard_delete_performed,
            moved=[
                ObsidianVaultMoveAppliedResponse.from_entity(item)
                for item in report.moved
            ],
            skipped=[
                ObsidianVaultMoveSkipResponse.from_entity(item)
                for item in report.skipped
            ],
            ambiguous=[
                ObsidianVaultMoveSkipResponse.from_entity(item)
                for item in report.ambiguous
            ],
            verification=ObsidianVaultMoveVerificationResponse(
                source_root_loose_notes_remaining=(
                    report.verification.source_root_loose_notes_remaining
                ),
                reindex_status=report.verification.reindex_status,
                verification_hits=report.verification.verification_hits,
            ),
            report_markdown_path=report.report_markdown_path,
            report_json_path=report.report_json_path,
        )


class ObsidianLibrarianJobResponse(StrictSchemaModel):
    """Status response for one Obsidian librarian execution job."""

    job_id: str
    status: ObsidianLibrarianJobStatus
    operation: str
    result_available: bool
    error_message: str | None
    created_at: AwareTimestamp
    updated_at: AwareTimestamp
    report_markdown_path: str | None
    report_json_path: str | None

    @classmethod
    def from_entity(cls, job: ObsidianLibrarianJob) -> ObsidianLibrarianJobResponse:
        """Create response from job snapshot.

        Args:
            job: Librarian job snapshot.

        Returns:
            Librarian job response.
        """
        report = job.report
        return cls(
            job_id=job.job_id,
            status=job.status,
            operation=job.operation,
            result_available=report is not None,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
            report_markdown_path=None
            if report is None
            else report.report_markdown_path,
            report_json_path=None if report is None else report.report_json_path,
        )
