"""Composite compatibility contract for Memory Compact persistence."""

from __future__ import annotations

from app.memory.domain.repositories.memory_compact_creation_repository import (
    IMemoryCompactCreationRepository,
)
from app.memory.domain.repositories.memory_compact_lifecycle_repository import (
    IMemoryCompactLifecycleRepository,
)
from app.memory.domain.repositories.memory_compact_repository_contracts import (
    MemoryCompactCreate,
    MemoryCompactSourceRefCreate,
)


class IMemoryCompactRepository(
    IMemoryCompactCreationRepository,
    IMemoryCompactLifecycleRepository,
):
    """Combine focused Memory Compact persistence ports for compatibility."""


__all__ = [
    "IMemoryCompactRepository",
    "MemoryCompactCreate",
    "MemoryCompactSourceRefCreate",
]
