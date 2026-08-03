"""Domain exceptions for Obsidian vault integration."""

from __future__ import annotations


class ObsidianDomainError(RuntimeError):
    """Base Obsidian integration exception."""


class ObsidianNotFoundError(ObsidianDomainError):
    """Raised when an Obsidian note or vault resource cannot be found."""


class ObsidianValidationError(ObsidianDomainError):
    """Raised when an Obsidian request violates a storage invariant."""


class ObsidianWriteConflictError(ObsidianDomainError):
    """Raised when a canonical note changed after an agent read it."""


class ObsidianIndexWriteError(ObsidianDomainError):
    """Raised when one rebuildable Obsidian index write fails."""


class ObsidianGraphUnavailableError(ObsidianDomainError):
    """Raised when a graph-only read is requested without a graph provider."""
