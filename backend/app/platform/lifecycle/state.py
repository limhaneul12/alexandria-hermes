"""In-memory process-local lifecycle state management.

This state is shared only within a single Python process. In uvicorn/gunicorn
multi-worker mode, each worker has its own lifecycle state.

This is currently a bootstrap implementation; when shared DB/Redis infrastructure
is introduced, drain coordination, short-lived failure counters, and lifecycle
event history should be revisited on external shared storage.
"""

from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock

from app.platform.lifecycle.dependency_health import (
    DependencyHealthStatus as DependencyHealthStatus,
)
from app.platform.lifecycle.dependency_status_store import DependencyStatusStore
from app.platform.lifecycle.snapshot import (
    LifecycleSnapshot,
    lifecycle_accepts_traffic,
    lifecycle_is_ready,
)
from app.platform.lifecycle.status import LifecycleStatus
from app.platform.lifecycle.transitions import (
    apply_drain_transition,
    apply_stopping_transition,
    status_when_marked_running,
)


class LifecycleState:
    """In-memory process-local lifecycle state store."""

    def __init__(self, *, started_at: datetime | None = None) -> None:
        """Initialize lifecycle state.

        Args:
            started_at: Process start timestamp, defaults to current UTC time.
        """
        self._lock = Lock()
        self._started_at = started_at or datetime.now(UTC)
        self._status = LifecycleStatus.STARTING
        self._dependencies = DependencyStatusStore()
        self._drain_started_at: datetime | None = None
        self._drain_reason: str | None = None

    def mark_running(self) -> None:
        """Transition state to ``running``.

        This transition is only allowed from ``starting`` or ``stopping``.
        Draining state does not auto-recover.

        Args:
            None.

        Returns:
            None.
        """
        with self._lock:
            self._status = status_when_marked_running(self._status)

    def mark_stopping(self) -> None:
        """Transition state to ``stopping``.

        Args:
            None.

        Returns:
            None.
        """
        with self._lock:
            self._status = apply_stopping_transition(self._dependencies)

    def mark_redis_starting(self) -> None:
        """Set Redis dependency status to ``starting``.

        Args:
            None.

        Returns:
            None.
        """
        with self._lock:
            self._dependencies.mark_redis_starting()

    def mark_redis_healthy(self) -> None:
        """Set Redis dependency status to healthy.

        Args:
            None.

        Returns:
            None.
        """
        with self._lock:
            self._dependencies.mark_redis_healthy(
                lifecycle_accepts_traffic=self._lifecycle_accepts_traffic(),
            )

    def mark_redis_unavailable(self) -> None:
        """Set Redis dependency status to ``unavailable``.

        Args:
            None.

        Returns:
            None.
        """
        with self._lock:
            self._dependencies.mark_redis_unavailable()

    def mark_redis_draining(self) -> None:
        """Set Redis dependency status to ``draining``.

        Args:
            None.

        Returns:
            None.
        """
        with self._lock:
            self._dependencies.mark_redis_draining()

    def mark_redis_disabled(self) -> None:
        """Set Redis dependency status to ``disabled``.

        Args:
            None.

        Returns:
            None.
        """
        with self._lock:
            self._dependencies.mark_redis_disabled()

    def mark_database_starting(self) -> None:
        """Set Database dependency status to ``starting``.

        Args:
            None.

        Returns:
            None.
        """
        with self._lock:
            self._dependencies.mark_database_starting()

    def mark_database_healthy(self) -> None:
        """Set Database dependency status to healthy.

        Args:
            None.

        Returns:
            None.
        """
        with self._lock:
            self._dependencies.mark_database_healthy(
                lifecycle_accepts_traffic=self._lifecycle_accepts_traffic(),
            )

    def mark_database_unavailable(self) -> None:
        """Set Database dependency status to ``unavailable``.

        Args:
            None.

        Returns:
            None.
        """
        with self._lock:
            self._dependencies.mark_database_unavailable()

    def mark_database_draining(self) -> None:
        """Set Database dependency status to ``draining``.

        Args:
            None.

        Returns:
            None.
        """
        with self._lock:
            self._dependencies.mark_database_draining()

    def mark_database_disabled(self) -> None:
        """Set Database dependency status to ``disabled``.

        Args:
            None.

        Returns:
            None.
        """
        with self._lock:
            self._dependencies.mark_database_disabled()

    def mark_minio_starting(self) -> None:
        """Set MINIO dependency status to ``starting``.

        Args:
            None.

        Returns:
            None.
        """
        with self._lock:
            self._dependencies.mark_minio_starting()

    def mark_minio_healthy(self) -> None:
        """Set MINIO dependency status to healthy.

        Args:
            None.

        Returns:
            None.
        """
        with self._lock:
            self._dependencies.mark_minio_healthy(
                lifecycle_accepts_traffic=self._lifecycle_accepts_traffic(),
            )

    def mark_minio_unavailable(self) -> None:
        """Set MINIO dependency status to ``unavailable``.

        Args:
            None.

        Returns:
            None.
        """
        with self._lock:
            self._dependencies.mark_minio_unavailable()

    def mark_minio_draining(self) -> None:
        """Set MINIO dependency status to ``draining``.

        Args:
            None.

        Returns:
            None.
        """
        with self._lock:
            self._dependencies.mark_minio_draining()

    def mark_minio_disabled(self) -> None:
        """Set MINIO dependency status to ``disabled``.

        Args:
            None.

        Returns:
            None.
        """
        with self._lock:
            self._dependencies.mark_minio_disabled()

    def start_draining(self, *, reason: str, now: datetime | None = None) -> bool:
        """Start draining state.

        Args:
            reason: Initial draining reason.
            now: Draining start timestamp, defaults to current UTC.

        Returns:
            ``True`` if this call initiated draining.
        """
        with self._lock:
            result = apply_drain_transition(
                status=self._status,
                dependencies=self._dependencies,
                reason=reason,
                now=now,
                drain_started_at=self._drain_started_at,
                drain_reason=self._drain_reason,
            )
            self._status = result.status
            self._drain_started_at = result.drain_started_at
            self._drain_reason = result.drain_reason
            return result.started

    def is_ready(self) -> bool:
        """Whether traffic can be accepted in the current state.

        Args:
            None.

        Returns:
            Return value.
        """
        with self._lock:
            ready = lifecycle_is_ready(
                status=self._status,
                dependencies=self._dependencies,
            )
            return ready

    def snapshot(self) -> LifecycleSnapshot:
        """Return a read-only snapshot of current lifecycle state.

        Args:
            None.

        Returns:
            Return value.
        """
        with self._lock:
            return LifecycleSnapshot(
                status=self._status,
                redis_status=self._dependencies.redis_status,
                database_status=self._dependencies.database_status,
                minio_status=self._dependencies.minio_status,
                started_at=self._started_at,
                drain_started_at=self._drain_started_at,
                drain_reason=self._drain_reason,
            )

    def _lifecycle_accepts_traffic(self) -> bool:
        accepts_traffic = lifecycle_accepts_traffic(self._status)
        return accepts_traffic
