"""Domain exceptions for Context Vault bounded-context use cases."""

from __future__ import annotations


class MemoryContextDomainError(RuntimeError):
    """Base Context Vault domain exception."""


class MemoryContextNotFoundError(MemoryContextDomainError):
    """Raised when a Context Vault resource cannot be located."""


class MemoryContextValidationError(MemoryContextDomainError):
    """Raised when a Context Vault invariant is violated."""
