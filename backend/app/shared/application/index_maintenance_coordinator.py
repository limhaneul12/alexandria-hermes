"""Fail-fast serialization for expensive rebuildable index operations."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.shared.exceptions.common_exceptions import IndexMaintenanceConflictError


class IndexMaintenanceCoordinator:
    """Serialize vault, embedding, and graph maintenance in one process."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._owner_task_id: int | None = None
        self._depth = 0
        self._active_operation: str | None = None

    @property
    def active_operation(self) -> str | None:
        """Return the outermost maintenance operation, when one is active.

        Returns:
            Active operation name, or ``None`` when the lane is idle.
        """
        return self._active_operation

    @asynccontextmanager
    async def operation(self, name: str) -> AsyncIterator[None]:
        """Enter one named operation or fail fast when another task owns it.

        Args:
            name: Stable name for the requested maintenance operation.

        Yields:
            Control while the current task owns the maintenance lane.
        """
        task = asyncio.current_task()
        if task is None:
            raise RuntimeError("index maintenance requires an active asyncio task")
        task_id = id(task)
        if self._owner_task_id == task_id:
            self._depth += 1
            try:
                yield
            finally:
                self._depth -= 1
            return
        if self._lock.locked():
            active = self._active_operation or "unknown"
            raise IndexMaintenanceConflictError(
                f"index maintenance '{name}' cannot start while '{active}' is active"
            )
        await self._lock.acquire()
        self._owner_task_id = task_id
        self._depth = 1
        self._active_operation = name
        try:
            yield
        finally:
            self._depth = 0
            self._owner_task_id = None
            self._active_operation = None
            self._lock.release()
