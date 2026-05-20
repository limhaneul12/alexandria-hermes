"""Domain exceptions for connections bounded-context use cases."""

from __future__ import annotations


class ConnectionsDomainError(RuntimeError):
    """Base connections domain exception."""


class ConnectionsResourceNotFoundError(ConnectionsDomainError):
    """Raised when a connections resource cannot be located."""


class ConnectionsProviderUnsupportedError(ConnectionsDomainError):
    """Raised when a provider cannot perform a connections operation."""
