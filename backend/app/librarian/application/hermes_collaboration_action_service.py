"""Backend-validated actions emitted by Hermes librarian delegates."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta

from app.librarian.domain.contracts.hermes_collaboration_contracts import (
    HermesLibrarianAskCommand,
    LibrarianDelegateResult,
)
from app.librarian.domain.event_enum.collaboration_enums import LibrarianDelegateStatus
from app.memory.application.memory_compact_service import MemoryCompactService
from app.memory.domain.event_enum.memory_compact_enums import MemoryCompactStatus
from app.memory.domain.repositories.memory_compact_repository import (
    MemoryCompactCreate,
    MemoryCompactSourceRefCreate,
)

_DAILY_MEMORY_COMPACT_MARKER = "ACTION: DAILY_MEMORY_COMPACT"
_LIBRARIAN_ACTION_SOURCE_TYPE = "LIBRARIAN_ACTION"
_DAILY_MEMORY_COMPACT_WINDOW = timedelta(days=1)


class HermesCollaborationActionService:
    """Apply supported librarian delegate actions through backend services."""

    def __init__(
        self,
        memory_compact_service: MemoryCompactService | None,
    ) -> None:
        """Initialize optional action dependencies.

        Args:
            memory_compact_service: Durable Memory Compact service when enabled.
        """
        self._memory_compact_service = memory_compact_service

    async def run(
        self,
        *,
        delegates: list[LibrarianDelegateResult],
        command: HermesLibrarianAskCommand,
        covered_to: datetime,
        job_id: str,
    ) -> tuple[list[LibrarianDelegateResult], list[str]]:
        """Apply supported delegate actions and return public route previews.

        Args:
            delegates: Delegate execution results.
            command: Original Hermes collaboration command.
            covered_to: End of the Memory Compact coverage window.
            job_id: Synthetic collaboration job identifier.

        Returns:
            Updated delegate results and applied action preview messages.
        """
        if self._memory_compact_service is None:
            return delegates, []
        updated: list[LibrarianDelegateResult] = []
        action_preview: list[str] = []
        action_source_refs = memory_compact_source_refs(command, job_id)
        for delegate in delegates:
            covered_from = covered_to - _DAILY_MEMORY_COMPACT_WINDOW
            compact_body = daily_memory_compact_body(
                delegate.summary,
                project=command.project,
                covered_from=covered_from,
                covered_to=covered_to,
            )
            if (
                delegate.status is not LibrarianDelegateStatus.COMPLETED
                or compact_body is None
            ):
                updated.append(delegate)
                continue
            compact = await self._memory_compact_service.create(
                MemoryCompactCreate(
                    project=command.project,
                    covered_from=covered_from,
                    covered_to=covered_to,
                    markdown_body=compact_body,
                    status=MemoryCompactStatus.CURRENT,
                    source_refs=tuple(action_source_refs),
                )
            )
            updated.append(
                replace(
                    delegate,
                    summary="\n\n".join(
                        [
                            "# Memory Compact saved",
                            f"- compact_id: {compact.id}",
                            f"- project: {compact.project or 'default'}",
                            "- coverage: last 24 hours",
                            "",
                            compact_body,
                        ]
                    ),
                )
            )
            action_preview.append(f"Saved daily Memory Compact: {compact.id}")
        return updated, action_preview


def daily_memory_compact_body(
    summary: str,
    *,
    project: str | None,
    covered_from: datetime,
    covered_to: datetime,
) -> str | None:
    """Return a validated daily Memory Compact body from a delegate summary.

    Args:
        summary: Delegate summary that may contain an action marker.
        project: Optional project scope.
        covered_from: Coverage window start.
        covered_to: Coverage window end.

    Returns:
        Canonical compact Markdown when the supported action is requested.
    """
    stripped = summary.strip()
    if not stripped.startswith(_DAILY_MEMORY_COMPACT_MARKER):
        return None
    compact_body = stripped[len(_DAILY_MEMORY_COMPACT_MARKER) :].lstrip()
    if not compact_body:
        return None
    return "\n".join(
        [
            "## Durable Decisions",
            "- Preserve the delegate-approved daily project memory as CURRENT.",
            "",
            "## Current State",
            compact_body,
            "",
            "## Risks and Blockers",
            "- None recorded by the delegate action.",
            "",
            "## Next Actions",
            "- Continue from this compact in the next session.",
            "",
            "## Coverage",
            f"- covered_from: {covered_from.isoformat()}",
            f"- covered_to: {covered_to.isoformat()}",
            f"- project: {project or 'default'}",
            "",
            "## Evidence Summary",
            "- Delegate-approved daily memory compact action.",
            "",
        ]
    )


def memory_compact_source_refs(
    command: HermesLibrarianAskCommand,
    job_id: str,
) -> list[MemoryCompactSourceRefCreate]:
    """Return source references for a delegate-created Memory Compact.

    Args:
        command: Original collaboration command.
        job_id: Synthetic collaboration job identifier.

    Returns:
        Explicit command source references or a collaboration fallback reference.
    """
    refs = [
        MemoryCompactSourceRefCreate(
            source_type=source_ref.source_type.value,
            source_id=source_ref.source_id,
            title=source_ref.title,
            detail_path=source_ref.detail_path,
        )
        for source_ref in command.source_refs
    ]
    if refs:
        return refs
    return [
        MemoryCompactSourceRefCreate(
            source_type=_LIBRARIAN_ACTION_SOURCE_TYPE,
            source_id=job_id,
            title="Librarian daily Memory Compact action",
            detail_path=f"/librarians/jobs/{job_id}",
        )
    ]
