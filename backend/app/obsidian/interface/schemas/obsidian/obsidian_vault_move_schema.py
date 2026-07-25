"""HTTP schemas for safe Obsidian vault move operations."""

from __future__ import annotations

from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianVaultMoveApplyRequest,
    ObsidianVaultMovePlanRequest,
    ObsidianVaultMoveRequest,
)
from app.obsidian.domain.entities.obsidian_note import (
    ObsidianVaultMoveApplied,
    ObsidianVaultMoveCandidate,
    ObsidianVaultMovePlan,
    ObsidianVaultMoveReport,
    ObsidianVaultMoveSkip,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from pydantic import Field


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
            moves=tuple(move.to_command() for move in self.moves)
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
            moves=tuple(move.to_command() for move in self.moves),
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
