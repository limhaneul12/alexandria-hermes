"""Librarian brief entity for provider-safe delegation inputs."""

from __future__ import annotations

from dataclasses import dataclass

from app.librarian.domain.entities.budget_policy import BudgetPolicy
from app.librarian.domain.entities.source_ref import SourceRef
from app.librarian.domain.types.librarian_brief_payload_types import (
    LibrarianBriefPayload,
)
from app.shared.exceptions.librarian_exceptions import LibrarianValidationError


@dataclass(frozen=True, slots=True, kw_only=True)
class LibrarianBrief:
    """Compiled knowledge packet sent to librarian delegates."""

    prompt: str
    project: str | None
    packet_markdown: str
    source_refs: tuple[SourceRef, ...]
    budget_policy: BudgetPolicy

    def __post_init__(self) -> None:
        """Validate brief invariants."""
        if not self.prompt.strip():
            raise LibrarianValidationError("prompt is required")
        if not self.packet_markdown.strip():
            raise LibrarianValidationError("packet_markdown is required")
        if len(self.packet_markdown) > self.budget_policy.max_input_chars:
            raise LibrarianValidationError("packet_markdown exceeds budget")
        if len(self.source_refs) > self.budget_policy.max_source_refs:
            raise LibrarianValidationError("source_refs exceed budget")

    def to_payload(self) -> LibrarianBriefPayload:
        """Return a public TypedDict payload.

        Returns:
            Public librarian brief payload.
        """
        return LibrarianBriefPayload(
            prompt=self.prompt,
            project=self.project,
            packet_markdown=self.packet_markdown,
            source_refs=[source_ref.to_payload() for source_ref in self.source_refs],
            budget_policy=self.budget_policy.to_payload(),
        )
