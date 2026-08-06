"""Portable Unix advisory lock for cross-process index write serialization."""

from __future__ import annotations

import asyncio
import fcntl
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path


class InterprocessFileLock:
    """Own one exclusive advisory file lease without blocking the event loop."""

    def __init__(
        self,
        lock_path: str | Path,
        *,
        poll_interval_seconds: float = 0.05,
    ) -> None:
        self._lock_path = Path(lock_path)
        self._poll_interval_seconds = poll_interval_seconds

    @property
    def lock_path(self) -> Path:
        """Return the durable advisory-lock path.

        Returns:
            Filesystem path used for the advisory lease.
        """
        return self._lock_path

    @asynccontextmanager
    async def operation(self, *, wait: bool) -> AsyncIterator[None]:
        """Acquire an exclusive lease and release it on every exit path.

        Args:
            wait: Whether to poll until the current process owner releases.

        Yields:
            Control while this process owns the advisory file lease.
        """
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        file_descriptor = os.open(
            self._lock_path,
            os.O_CREAT | os.O_RDWR,
            0o600,
        )
        acquired = False
        try:
            while True:
                try:
                    fcntl.flock(
                        file_descriptor,
                        fcntl.LOCK_EX | fcntl.LOCK_NB,
                    )
                except BlockingIOError:
                    if not wait:
                        raise
                    await asyncio.sleep(self._poll_interval_seconds)
                    continue
                acquired = True
                break
            yield
        finally:
            if acquired:
                fcntl.flock(file_descriptor, fcntl.LOCK_UN)
            os.close(file_descriptor)
