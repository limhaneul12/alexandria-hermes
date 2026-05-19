"""Domain exceptions for librarian bounded-context use cases."""

from __future__ import annotations


class LibrarianDomainError(RuntimeError):
    """Base librarian domain exception."""


class LibrarianValidationError(LibrarianDomainError):
    """Raised when librarian domain values violate invariants."""


class LibrarianSkillAcquisitionProviderError(LibrarianDomainError):
    """Raised when a skill-acquisition provider cannot be used."""


class LibrarianSkillAcquisitionExecutionError(LibrarianDomainError):
    """Raised when provider execution fails during skill acquisition."""


class LibrarianSkillAcquisitionArtifactError(LibrarianValidationError):
    """Raised when a provider returns an invalid skill artifact."""
