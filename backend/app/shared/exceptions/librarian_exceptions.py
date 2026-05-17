"""Domain exceptions for librarian bounded-context use cases."""

from __future__ import annotations


class LibrarianDomainError(RuntimeError):
    """Base librarian domain exception."""


class LibrarianValidationError(LibrarianDomainError):
    """Raised when librarian domain values violate invariants."""
