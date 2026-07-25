"""HTTP schemas for Obsidian librarian review operations."""

from __future__ import annotations

from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianLibrarianReviewApplyRequest,
    ObsidianLibrarianReviewQueueRequest,
)
from app.obsidian.domain.entities.obsidian_note import (
    ObsidianLibrarianReviewQueueItem,
)
from app.obsidian.domain.event_enum.obsidian_enums import (
    AlexandriaNoteType,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from pydantic import Field


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
