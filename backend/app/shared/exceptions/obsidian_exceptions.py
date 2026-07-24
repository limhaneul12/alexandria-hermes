"""Domain exceptions for Obsidian vault integration."""

from __future__ import annotations


class ObsidianDomainError(RuntimeError):
    """Base Obsidian integration exception."""


class ObsidianNotFoundError(ObsidianDomainError):
    """Raised when an Obsidian note or vault resource cannot be found."""


class ObsidianValidationError(ObsidianDomainError):
    """Raised when an Obsidian request violates a storage invariant."""


class ObsidianIndexWriteError(ObsidianDomainError):
    """Raised when one rebuildable Obsidian index write fails."""
