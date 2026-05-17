"""Compact context packet entity for librarian brief compilation."""

from __future__ import annotations

from dataclasses import dataclass

from app.librarian.domain.entities.source_ref import SourceRef
from app.librarian.domain.types.librarian_brief_payload_types import (
    ContextPackCompactPayload,
)
from app.shared.exceptions.librarian_exceptions import LibrarianValidationError


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextPackCompact:
    """Budget-ready context summary plus lazy source references."""

    markdown_body: str
    source_refs: tuple[SourceRef, ...] = ()

    def __post_init__(self) -> None:
        """Validate compact body."""
        if not self.markdown_body.strip():
            raise LibrarianValidationError("markdown_body is required")

    def to_payload(self) -> ContextPackCompactPayload:
        """Return a public TypedDict payload.

        Returns:
            Public context-pack compact payload.
        """
        return ContextPackCompactPayload(
            markdown_body=self.markdown_body,
            source_refs=[source_ref.to_payload() for source_ref in self.source_refs],
        )
