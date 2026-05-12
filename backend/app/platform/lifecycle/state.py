"""In-memory process-local lifecycle state management.

This state is shared only within a single Python process. In uvicorn/gunicorn
multi-worker mode, each worker has its own lifecycle state.

This is currently a bootstrap implementation; when shared DB/Redis infrastructure
is introduced, drain coordination, short-lived failure counters, and lifecycle
event history should be revisited on external shared storage.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from threading import Lock


class LifecycleStatus(StrEnum):
    """Lifecycle status values for the service."""

    STARTING = "starting"
    RUNNING = "running"
    DRAINING = "draining"
    STOPPING = "stopping"


class DependencyHealthStatus(StrEnum):
    """Shared dependency health states."""

    DISABLED = "disabled"
    STARTING = "starting"
    OK = "ok"
    DRAINING = "draining"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class LifecycleSnapshot:
    """Read-only snapshot of lifecycle state."""

    status: LifecycleStatus
    redis_status: DependencyHealthStatus
    database_status: DependencyHealthStatus
    started_at: datetime
    drain_started_at: datetime | None
    drain_reason: str | None

    @property
    def draining(self) -> bool:
        """Whether the lifecycle state is currently ``draining``.

        Args:
            None.

        Return:
            Return value.
        """
        return self.status is LifecycleStatus.DRAINING

    @property
    def ready(self) -> bool:
        """Whether the service is ready to accept new traffic.

        Args:
            None.

        Return:
            Return value.
        """
        return (
            self.status is LifecycleStatus.RUNNING
            and dependency_is_ready(self.redis_status)
            and dependency_is_ready(self.database_status)
        )


def dependency_is_ready(status: DependencyHealthStatus) -> bool:
    """Check if a dependency status permits readiness.

    Args:
        status: See function signature.

    Return:
        Return value.
    """
    return status in {
        DependencyHealthStatus.DISABLED,
        DependencyHealthStatus.OK,
    }


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
        self._redis_status = DependencyHealthStatus.DISABLED
        self._database_status = DependencyHealthStatus.DISABLED
        self._drain_started_at: datetime | None = None
        self._drain_reason: str | None = None

    def mark_running(self) -> None:
        """Transition state to ``running``.

        This transition is only allowed from ``starting`` or ``stopping``.
        Draining state does not auto-recover.

        Args:
            None.

        Return:
            None.
        """
        with self._lock:
            if self._status in {LifecycleStatus.STARTING, LifecycleStatus.STOPPING}:
                self._status = LifecycleStatus.RUNNING

    def mark_stopping(self) -> None:
        """Transition state to ``stopping``.

        Args:
            None.

        Return:
            None.
        """
        with self._lock:
            self._status = LifecycleStatus.STOPPING
            self._redis_status = _drain_dependency(self._redis_status)
            self._database_status = _drain_dependency(self._database_status)

    def mark_redis_starting(self) -> None:
        """Set Redis dependency status to ``starting``.

        Args:
            None.

        Return:
            None.
        """
        with self._lock:
            self._redis_status = DependencyHealthStatus.STARTING

    def mark_redis_healthy(self) -> None:
        """Set Redis dependency status to healthy.

        Args:
            None.

        Return:
            None.
        """
        with self._lock:
            self._redis_status = self._healthy_dependency_status()

    def mark_redis_unavailable(self) -> None:
        """Set Redis dependency status to ``unavailable``.

        Args:
            None.

        Return:
            None.
        """
        with self._lock:
            self._redis_status = DependencyHealthStatus.UNAVAILABLE

    def mark_redis_draining(self) -> None:
        """Set Redis dependency status to ``draining``.

        Args:
            None.

        Return:
            None.
        """
        with self._lock:
            self._redis_status = _drain_dependency(self._redis_status)

    def mark_redis_disabled(self) -> None:
        """Set Redis dependency status to ``disabled``.

        Args:
            None.

        Return:
            None.
        """
        with self._lock:
            self._redis_status = DependencyHealthStatus.DISABLED

    def mark_database_starting(self) -> None:
        """Set Database dependency status to ``starting``.

        Args:
            None.

        Return:
            None.
        """
        with self._lock:
            self._database_status = DependencyHealthStatus.STARTING

    def mark_database_healthy(self) -> None:
        """Set Database dependency status to healthy.

        Args:
            None.

        Return:
            None.
        """
        with self._lock:
            self._database_status = self._healthy_dependency_status()

    def mark_database_unavailable(self) -> None:
        """Set Database dependency status to ``unavailable``.

        Args:
            None.

        Return:
            None.
        """
        with self._lock:
            self._database_status = DependencyHealthStatus.UNAVAILABLE

    def mark_database_draining(self) -> None:
        """Set Database dependency status to ``draining``.

        Args:
            None.

        Return:
            None.
        """
        with self._lock:
            self._database_status = _drain_dependency(self._database_status)

    def mark_database_disabled(self) -> None:
        """Set Database dependency status to ``disabled``.

        Args:
            None.

        Return:
            None.
        """
        with self._lock:
            self._database_status = DependencyHealthStatus.DISABLED

    def start_draining(self, *, reason: str, now: datetime | None = None) -> bool:
        """Start draining state.

        Args:
            reason: Initial draining reason.
            now: Draining start timestamp, defaults to current UTC.

        Return:
            ``True`` if this call initiated draining.
        """
        with self._lock:
            if self._status is LifecycleStatus.DRAINING:
                return False
            if self._status is LifecycleStatus.STOPPING:
                return False
            self._status = LifecycleStatus.DRAINING
            self._redis_status = _drain_dependency(self._redis_status)
            self._database_status = _drain_dependency(self._database_status)
            self._drain_started_at = now or datetime.now(UTC)
            self._drain_reason = reason
            return True

    def is_ready(self) -> bool:
        """Whether traffic can be accepted in the current state.

        Args:
            None.

        Return:
            Return value.
        """
        with self._lock:
            return (
                self._status is LifecycleStatus.RUNNING
                and dependency_is_ready(self._redis_status)
                and dependency_is_ready(self._database_status)
            )

    def snapshot(self) -> LifecycleSnapshot:
        """Return a read-only snapshot of current lifecycle state.

        Args:
            None.

        Return:
            Return value.
        """
        with self._lock:
            return LifecycleSnapshot(
                status=self._status,
                redis_status=self._redis_status,
                database_status=self._database_status,
                started_at=self._started_at,
                drain_started_at=self._drain_started_at,
                drain_reason=self._drain_reason,
            )

    def _healthy_dependency_status(self) -> DependencyHealthStatus:
        if self._status in {LifecycleStatus.DRAINING, LifecycleStatus.STOPPING}:
            return DependencyHealthStatus.DRAINING
        return DependencyHealthStatus.OK


def _drain_dependency(status: DependencyHealthStatus) -> DependencyHealthStatus:
    if status is DependencyHealthStatus.OK:
        return DependencyHealthStatus.DRAINING
    return status
