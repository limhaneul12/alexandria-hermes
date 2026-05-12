"""Domain exceptions for library bounded-context use cases."""

from __future__ import annotations


class LibraryDomainError(RuntimeError):
    """Base library domain exception."""


class LibraryResourceNotFoundError(LibraryDomainError):
    """Raised when a requested library resource cannot be located."""


class LibraryValidationError(LibraryDomainError):
    """Raised when library request data violates domain invariants."""


class LibraryCategoryCycleError(LibraryValidationError):
    """Raised when a category move creates a cycle."""


class LibraryProviderUnsupportedError(LibraryDomainError):
    """Raised when a librarian provider cannot perform the requested action."""


# Backwards-compatible aliases for existing application/repository imports.
NotFoundError = LibraryResourceNotFoundError
ValidationError = LibraryValidationError
CircularCategoryError = LibraryCategoryCycleError
UnsupportedProviderError = LibraryProviderUnsupportedError
