"""Process-wide serialization for rebuildable index write operations."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Protocol

from app.shared.exceptions.common_exceptions import IndexMaintenanceConflictError


class IndexWriteProcessLock(Protocol):
    """Cross-process exclusive lease for one rebuildable index database."""

    def operation(self, *, wait: bool) -> AbstractAsyncContextManager[None]:
        """Return one exclusive process-lock operation context.

        Args:
            wait: Whether the caller should wait for another process to release.

        Returns:
            Async context manager that owns the cross-process lease.
        """


class IndexMaintenanceCoordinator:
    """Serialize every write to the rebuildable index surfaces in one process.

    Maintenance callers retain fail-fast behavior, while short canonical note
    writes may queue behind an active maintenance operation.  The coordinator
    is re-entrant for one asyncio task so a report bundle can own the lane and
    call nested note, reindex, embedding, and graph operations safely.
    """

    def __init__(
        self,
        *,
        process_lock: IndexWriteProcessLock | None = None,
    ) -> None:
        self._lock = asyncio.Lock()
        self._process_lock = process_lock
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
    async def operation(
        self,
        name: str,
        *,
        wait: bool = False,
    ) -> AsyncIterator[None]:
        """Enter one named operation.

        Args:
            name: Stable name for the requested index write operation.
            wait: Queue behind the current owner instead of failing fast.

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
        if self._lock.locked() and not wait:
            active = self._active_operation or "unknown"
            raise IndexMaintenanceConflictError(
                f"index maintenance '{name}' cannot start while '{active}' is active"
            )
        await self._lock.acquire()
        self._owner_task_id = task_id
        self._depth = 1
        self._active_operation = name
        try:
            if self._process_lock is None:
                yield
            else:
                try:
                    async with self._process_lock.operation(wait=wait):
                        yield
                except BlockingIOError as exc:
                    raise IndexMaintenanceConflictError(
                        f"index maintenance '{name}' cannot start because another "
                        "process owns the index write lane"
                    ) from exc
        finally:
            self._depth = 0
            self._owner_task_id = None
            self._active_operation = None
            self._lock.release()

    @asynccontextmanager
    async def write_operation(self, name: str) -> AsyncIterator[None]:
        """Queue one short canonical/index write behind the active operation.

        Args:
            name: Stable name for the canonical/index write.

        Yields:
            Control while the current task owns both write lanes.
        """
        async with self.operation(name, wait=True):
            yield
