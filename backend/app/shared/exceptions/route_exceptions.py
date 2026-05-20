"""Shared route exception mapping contracts."""

from __future__ import annotations

from app.shared.exceptions.common_exceptions import BoundaryValidationError
from app.shared.exceptions.connections_exceptions import (
    ConnectionsProviderUnsupportedError,
    ConnectionsResourceNotFoundError,
)
from app.shared.exceptions.exception_decorators import RouteExceptionStatusMapping
from app.shared.exceptions.librarian_exceptions import (
    LibrarianProviderUnsupportedError,
    LibrarianResourceNotFoundError,
    LibrarianValidationError,
)
from app.shared.exceptions.library_exceptions import (
    LibraryCategoryCycleError,
    LibraryProviderUnsupportedError,
    LibraryResourceNotFoundError,
    LibraryValidationError,
)
from app.shared.exceptions.memory_compact_exceptions import (
    MemoryCompactNotFoundError,
    MemoryCompactValidationError,
)
from app.shared.exceptions.memory_context_exceptions import (
    MemoryContextNotFoundError,
    MemoryContextValidationError,
)
from fastapi import status

LIBRARY_ROUTE_EXCEPTION_MAPPING: RouteExceptionStatusMapping = {
    BoundaryValidationError: status.HTTP_400_BAD_REQUEST,
    LibraryCategoryCycleError: status.HTTP_409_CONFLICT,
    LibraryProviderUnsupportedError: status.HTTP_400_BAD_REQUEST,
    LibraryResourceNotFoundError: status.HTTP_404_NOT_FOUND,
    LibraryValidationError: status.HTTP_400_BAD_REQUEST,
}

CONNECTIONS_PROVIDER_TEST_EXCEPTION_MAPPING: RouteExceptionStatusMapping = {
    ConnectionsResourceNotFoundError: (
        status.HTTP_404_NOT_FOUND,
        "Provider not found",
    ),
}

MEMORY_COMPACT_ROUTE_EXCEPTION_MAPPING: RouteExceptionStatusMapping = {
    BoundaryValidationError: status.HTTP_400_BAD_REQUEST,
    MemoryCompactNotFoundError: status.HTTP_404_NOT_FOUND,
    MemoryCompactValidationError: status.HTTP_400_BAD_REQUEST,
}

ARCHIVE_ROUTE_EXCEPTION_MAPPING: RouteExceptionStatusMapping = {
    **LIBRARY_ROUTE_EXCEPTION_MAPPING,
}

CONNECTIONS_ROUTE_EXCEPTION_MAPPING: RouteExceptionStatusMapping = {
    BoundaryValidationError: status.HTTP_400_BAD_REQUEST,
    ConnectionsProviderUnsupportedError: status.HTTP_400_BAD_REQUEST,
    ConnectionsResourceNotFoundError: status.HTTP_404_NOT_FOUND,
}

CONTEXT_ROUTE_EXCEPTION_MAPPING: RouteExceptionStatusMapping = {
    BoundaryValidationError: status.HTTP_400_BAD_REQUEST,
    MemoryContextNotFoundError: status.HTTP_404_NOT_FOUND,
    MemoryContextValidationError: status.HTTP_400_BAD_REQUEST,
}

LIBRARIAN_ROUTE_EXCEPTION_MAPPING: RouteExceptionStatusMapping = {
    BoundaryValidationError: status.HTTP_400_BAD_REQUEST,
    LibrarianProviderUnsupportedError: status.HTTP_400_BAD_REQUEST,
    LibrarianResourceNotFoundError: status.HTTP_404_NOT_FOUND,
    LibrarianValidationError: status.HTTP_400_BAD_REQUEST,
}

RETRIEVAL_ROUTE_EXCEPTION_MAPPING: RouteExceptionStatusMapping = {
    **LIBRARY_ROUTE_EXCEPTION_MAPPING,
}
