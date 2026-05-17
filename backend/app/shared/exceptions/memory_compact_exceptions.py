"""Shared exceptions for Memory Compact bounded-context use cases."""

from __future__ import annotations


class MemoryCompactDomainError(RuntimeError):
    """Base Memory Compact domain exception."""


class MemoryCompactNotFoundError(MemoryCompactDomainError):
    """Raised when a Memory Compact artifact cannot be located."""


class MemoryCompactValidationError(MemoryCompactDomainError):
    """Raised when a Memory Compact invariant is violated."""
