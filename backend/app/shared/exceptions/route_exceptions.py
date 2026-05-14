"""Shared route exception mapping contracts."""

from __future__ import annotations

from app.shared.exceptions.exception_decorators import RouteExceptionStatusMapping
from app.shared.exceptions.library_exceptions import (
    LibraryCategoryCycleError,
    LibraryProviderUnsupportedError,
    LibraryResourceNotFoundError,
    LibraryValidationError,
)
from fastapi import status

LIBRARY_ROUTE_EXCEPTION_MAPPING: RouteExceptionStatusMapping = {
    LibraryCategoryCycleError: status.HTTP_409_CONFLICT,
    LibraryProviderUnsupportedError: status.HTTP_400_BAD_REQUEST,
    LibraryResourceNotFoundError: status.HTTP_404_NOT_FOUND,
    LibraryValidationError: status.HTTP_400_BAD_REQUEST,
}

LIBRARY_PROVIDER_TEST_EXCEPTION_MAPPING: RouteExceptionStatusMapping = {
    LibraryResourceNotFoundError: (status.HTTP_404_NOT_FOUND, "Provider not found"),
}
