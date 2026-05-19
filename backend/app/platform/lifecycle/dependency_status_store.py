"""Dependency status store for platform lifecycle state."""

from __future__ import annotations

from dataclasses import dataclass

from app.platform.lifecycle.dependency_health import (
    DependencyHealthStatus,
    dependency_status_when_lifecycle_drains,
    dependency_status_when_marked_healthy,
)


@dataclass(slots=True)
class DependencyStatusStore:
    """Mutable lifecycle-owned dependency health status store."""

    redis_status: DependencyHealthStatus = DependencyHealthStatus.DISABLED
    database_status: DependencyHealthStatus = DependencyHealthStatus.DISABLED

    def mark_all_draining(self) -> None:
        """Move all healthy dependencies to draining state.

        Args:
            None.

        Returns:
            None.
        """
        self.redis_status = dependency_status_when_lifecycle_drains(self.redis_status)
        self.database_status = dependency_status_when_lifecycle_drains(
            self.database_status,
        )

    def mark_redis_starting(self) -> None:
        """Set Redis dependency status to starting.

        Args:
            None.

        Returns:
            None.
        """
        self.redis_status = DependencyHealthStatus.STARTING

    def mark_redis_healthy(self, *, lifecycle_accepts_traffic: bool) -> None:
        """Set Redis dependency status from a healthy report.

        Args:
            lifecycle_accepts_traffic: Whether lifecycle may accept traffic.

        Returns:
            None.
        """
        self.redis_status = dependency_status_when_marked_healthy(
            lifecycle_accepts_traffic=lifecycle_accepts_traffic,
        )

    def mark_redis_unavailable(self) -> None:
        """Set Redis dependency status to unavailable.

        Args:
            None.

        Returns:
            None.
        """
        self.redis_status = DependencyHealthStatus.UNAVAILABLE

    def mark_redis_draining(self) -> None:
        """Move healthy Redis status to draining state.

        Args:
            None.

        Returns:
            None.
        """
        self.redis_status = dependency_status_when_lifecycle_drains(self.redis_status)

    def mark_redis_disabled(self) -> None:
        """Set Redis dependency status to disabled.

        Args:
            None.

        Returns:
            None.
        """
        self.redis_status = DependencyHealthStatus.DISABLED

    def mark_database_starting(self) -> None:
        """Set Database dependency status to starting.

        Args:
            None.

        Returns:
            None.
        """
        self.database_status = DependencyHealthStatus.STARTING

    def mark_database_healthy(self, *, lifecycle_accepts_traffic: bool) -> None:
        """Set Database dependency status from a healthy report.

        Args:
            lifecycle_accepts_traffic: Whether lifecycle may accept traffic.

        Returns:
            None.
        """
        self.database_status = dependency_status_when_marked_healthy(
            lifecycle_accepts_traffic=lifecycle_accepts_traffic,
        )

    def mark_database_unavailable(self) -> None:
        """Set Database dependency status to unavailable.

        Args:
            None.

        Returns:
            None.
        """
        self.database_status = DependencyHealthStatus.UNAVAILABLE

    def mark_database_draining(self) -> None:
        """Move healthy Database status to draining state.

        Args:
            None.

        Returns:
            None.
        """
        self.database_status = dependency_status_when_lifecycle_drains(
            self.database_status,
        )

    def mark_database_disabled(self) -> None:
        """Set Database dependency status to disabled.

        Args:
            None.

        Returns:
            None.
        """
        self.database_status = DependencyHealthStatus.DISABLED
