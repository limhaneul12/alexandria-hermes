"""HTTP schema for Obsidian librarian workflow job status."""

from __future__ import annotations

from app.obsidian.domain.entities.obsidian_note import (
    ObsidianLibrarianJob,
)
from app.obsidian.domain.event_enum.obsidian_enums import (
    ObsidianLibrarianJobStatus,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.schemas.datetime_schemas import AwareTimestamp


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
