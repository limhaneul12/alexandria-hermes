"""Budget policy entity for librarian knowledge packets."""

from __future__ import annotations

from dataclasses import dataclass

from app.librarian.domain.types.librarian_brief_payload_types import BudgetPolicyPayload
from app.shared.exceptions.librarian_exceptions import LibrarianValidationError


@dataclass(frozen=True, slots=True, kw_only=True)
class BudgetPolicy:
    """Packet size and source-reference limits for librarian calls."""

    max_input_chars: int = 12_000
    max_source_refs: int = 20
    max_preview_chars: int = 800

    def __post_init__(self) -> None:
        """Validate positive budget fields."""
        if self.max_input_chars <= 0:
            raise LibrarianValidationError("max_input_chars must be positive")
        if self.max_source_refs <= 0:
            raise LibrarianValidationError("max_source_refs must be positive")
        if self.max_preview_chars <= 0:
            raise LibrarianValidationError("max_preview_chars must be positive")

    def to_payload(self) -> BudgetPolicyPayload:
        """Return a public TypedDict payload.

        Returns:
            Public budget policy payload.
        """
        return BudgetPolicyPayload(
            max_input_chars=self.max_input_chars,
            max_source_refs=self.max_source_refs,
            max_preview_chars=self.max_preview_chars,
        )
