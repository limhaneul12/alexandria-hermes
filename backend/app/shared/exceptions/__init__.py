"""Shared backend exception catalog."""

from .library_exceptions import (
    CircularCategoryError,
    LibraryCategoryCycleError,
    LibraryDomainError,
    LibraryProviderUnsupportedError,
    LibraryResourceNotFoundError,
    LibraryValidationError,
    NotFoundError,
    UnsupportedProviderError,
    ValidationError,
)

__all__ = [
    "CircularCategoryError",
    "LibraryCategoryCycleError",
    "LibraryDomainError",
    "LibraryProviderUnsupportedError",
    "LibraryResourceNotFoundError",
    "LibraryValidationError",
    "NotFoundError",
    "UnsupportedProviderError",
    "ValidationError",
]
