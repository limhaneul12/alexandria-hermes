"""Shared backend exception catalog."""

from .common_exceptions import (
    BoundaryValidationError,
    RedisExceptionAction,
    RedisExceptionArgValue,
    RedisExceptionAware,
    RedisExceptionDecorator,
    RedisExceptionHandler,
    RedisExceptionKwargs,
    RedisExceptionPayload,
    RedisExceptionPolicy,
    RedisExceptionPolicyMap,
    RedisExceptionRawData,
    RedisExceptionResult,
)
from .connections_exceptions import (
    ConnectionsDomainError,
    ConnectionsProviderUnsupportedError,
    ConnectionsResourceNotFoundError,
)
from .exception_decorators import router_exception_status
from .librarian_exceptions import (
    LibrarianDomainError,
    LibrarianProviderUnsupportedError,
    LibrarianResourceNotFoundError,
    LibrarianSkillAcquisitionArtifactError,
    LibrarianSkillAcquisitionExecutionError,
    LibrarianSkillAcquisitionProviderError,
    LibrarianValidationError,
)
from .library_exceptions import (
    LibraryCategoryCycleError,
    LibraryDomainError,
    LibraryProviderUnsupportedError,
    LibraryResourceNotFoundError,
    LibraryValidationError,
)
from .memory_compact_exceptions import (
    MemoryCompactDomainError,
    MemoryCompactNotFoundError,
    MemoryCompactValidationError,
)
from .memory_context_exceptions import (
    MemoryContextDomainError,
    MemoryContextNotFoundError,
    MemoryContextValidationError,
)
from .route_exceptions import (
    ARCHIVE_ROUTE_EXCEPTION_MAPPING,
    CONNECTIONS_PROVIDER_TEST_EXCEPTION_MAPPING,
    CONNECTIONS_ROUTE_EXCEPTION_MAPPING,
    CONTEXT_ROUTE_EXCEPTION_MAPPING,
    LIBRARIAN_ROUTE_EXCEPTION_MAPPING,
    LIBRARY_ROUTE_EXCEPTION_MAPPING,
    MEMORY_COMPACT_ROUTE_EXCEPTION_MAPPING,
    RETRIEVAL_ROUTE_EXCEPTION_MAPPING,
)

__all__ = [
    "ARCHIVE_ROUTE_EXCEPTION_MAPPING",
    "CONNECTIONS_PROVIDER_TEST_EXCEPTION_MAPPING",
    "CONNECTIONS_ROUTE_EXCEPTION_MAPPING",
    "CONTEXT_ROUTE_EXCEPTION_MAPPING",
    "LIBRARIAN_ROUTE_EXCEPTION_MAPPING",
    "LIBRARY_ROUTE_EXCEPTION_MAPPING",
    "MEMORY_COMPACT_ROUTE_EXCEPTION_MAPPING",
    "RETRIEVAL_ROUTE_EXCEPTION_MAPPING",
    "BoundaryValidationError",
    "ConnectionsDomainError",
    "ConnectionsProviderUnsupportedError",
    "ConnectionsResourceNotFoundError",
    "LibrarianDomainError",
    "LibrarianProviderUnsupportedError",
    "LibrarianResourceNotFoundError",
    "LibrarianSkillAcquisitionArtifactError",
    "LibrarianSkillAcquisitionExecutionError",
    "LibrarianSkillAcquisitionProviderError",
    "LibrarianValidationError",
    "LibraryCategoryCycleError",
    "LibraryDomainError",
    "LibraryProviderUnsupportedError",
    "LibraryResourceNotFoundError",
    "LibraryValidationError",
    "MemoryCompactDomainError",
    "MemoryCompactNotFoundError",
    "MemoryCompactValidationError",
    "MemoryContextDomainError",
    "MemoryContextNotFoundError",
    "MemoryContextValidationError",
    "RedisExceptionAction",
    "RedisExceptionArgValue",
    "RedisExceptionAware",
    "RedisExceptionDecorator",
    "RedisExceptionHandler",
    "RedisExceptionKwargs",
    "RedisExceptionPayload",
    "RedisExceptionPolicy",
    "RedisExceptionPolicyMap",
    "RedisExceptionRawData",
    "RedisExceptionResult",
    "router_exception_status",
]
