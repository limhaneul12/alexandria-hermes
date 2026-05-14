"""Shared backend exception catalog."""

from .common_exceptions import (
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
from .exception_decorators import router_exception_status
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
from .route_exceptions import (
    LIBRARY_PROVIDER_TEST_EXCEPTION_MAPPING,
    LIBRARY_ROUTE_EXCEPTION_MAPPING,
)

__all__ = [
    "LIBRARY_PROVIDER_TEST_EXCEPTION_MAPPING",
    "LIBRARY_ROUTE_EXCEPTION_MAPPING",
    "CircularCategoryError",
    "LibraryCategoryCycleError",
    "LibraryDomainError",
    "LibraryProviderUnsupportedError",
    "LibraryResourceNotFoundError",
    "LibraryValidationError",
    "NotFoundError",
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
    "UnsupportedProviderError",
    "ValidationError",
    "router_exception_status",
]
