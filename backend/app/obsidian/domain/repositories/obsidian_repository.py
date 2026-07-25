"""Compatibility repository ports for Obsidian index and workflows."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.obsidian.domain.entities.obsidian_note import ObsidianLibrarianWorkflow
from app.obsidian.domain.repositories.obsidian_index_error_repository import (
    IObsidianIndexErrorRepository,
)
from app.obsidian.domain.repositories.obsidian_index_query_repository import (
    IObsidianIndexQueryRepository,
)
from app.obsidian.domain.repositories.obsidian_index_write_repository import (
    IObsidianIndexWriteRepository,
)


class IObsidianIndexRepository(
    IObsidianIndexWriteRepository,
    IObsidianIndexQueryRepository,
    IObsidianIndexErrorRepository,
):
    """Combine focused Obsidian index ports for application compatibility."""


class IObsidianWorkflowRepository(ABC):
    """Persistence contract for librarian workflow checkpoints."""

    @abstractmethod
    async def upsert_workflow(self, workflow: ObsidianLibrarianWorkflow) -> None:
        """Persist one workflow checkpoint.

        Args:
            workflow: Workflow checkpoint entity.
        """

    @abstractmethod
    async def get_workflow(self, thread_id: str) -> ObsidianLibrarianWorkflow | None:
        """Read one workflow checkpoint by thread id.

        Args:
            thread_id: Workflow thread id.

        Returns:
            Workflow when found.
        """
