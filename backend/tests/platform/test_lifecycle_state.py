"""Behavior tests for platform lifecycle dependency state."""

from __future__ import annotations

import pytest
from app.platform.lifecycle.dependency_health import (
    DependencyHealthStatus,
    dependency_status_when_lifecycle_drains,
    dependency_status_when_marked_healthy,
)
from app.platform.lifecycle.dependency_status_store import DependencyStatusStore
from app.platform.lifecycle.state import LifecycleState
from app.platform.lifecycle.status import LifecycleStatus


def test_lifecycle_ready_includes_minio_dependency_when_enabled() -> None:
    """Readiness turns false when enabled MINIO integration is unavailable."""
    lifecycle = LifecycleState()
    lifecycle.mark_database_healthy()
    lifecycle.mark_minio_unavailable()
    lifecycle.mark_running()

    snapshot = lifecycle.snapshot()

    assert snapshot.ready is False
    assert snapshot.minio_status is DependencyHealthStatus.UNAVAILABLE


def test_lifecycle_draining_marks_healthy_minio_as_draining() -> None:
    """MINIO dependency enters drain state with the rest of lifecycle dependencies."""
    lifecycle = LifecycleState()
    lifecycle.mark_minio_healthy()

    lifecycle.start_draining(reason="shutdown")

    assert lifecycle.snapshot().minio_status is DependencyHealthStatus.DRAINING


def test_dependency_status_store_marks_all_healthy_dependencies_draining() -> None:
    """Dependency status store drains only dependencies currently ready for traffic."""
    dependencies = DependencyStatusStore(
        redis_status=DependencyHealthStatus.OK,
        database_status=DependencyHealthStatus.DISABLED,
        minio_status=DependencyHealthStatus.UNAVAILABLE,
    )

    dependencies.mark_all_draining()

    assert dependencies == DependencyStatusStore(
        redis_status=DependencyHealthStatus.DRAINING,
        database_status=DependencyHealthStatus.DISABLED,
        minio_status=DependencyHealthStatus.UNAVAILABLE,
    )


@pytest.mark.parametrize(
    ("current_status", "drained_status"),
    [
        (DependencyHealthStatus.DISABLED, DependencyHealthStatus.DISABLED),
        (DependencyHealthStatus.STARTING, DependencyHealthStatus.STARTING),
        (DependencyHealthStatus.OK, DependencyHealthStatus.DRAINING),
        (DependencyHealthStatus.DRAINING, DependencyHealthStatus.DRAINING),
        (DependencyHealthStatus.UNAVAILABLE, DependencyHealthStatus.UNAVAILABLE),
    ],
)
def test_dependency_drain_policy_preserves_only_non_healthy_states(
    current_status: DependencyHealthStatus,
    drained_status: DependencyHealthStatus,
) -> None:
    """Dependency drain policy only moves healthy dependencies into draining."""
    assert dependency_status_when_lifecycle_drains(current_status) is drained_status


def test_dependency_health_policy_returns_draining_when_lifecycle_rejects_traffic() -> (
    None
):
    """Healthy dependency reports are draining while lifecycle rejects traffic."""
    assert (
        dependency_status_when_marked_healthy(lifecycle_accepts_traffic=False)
        is DependencyHealthStatus.DRAINING
    )


def test_lifecycle_running_transition_does_not_recover_from_draining() -> None:
    """Running transition preserves active drain state until process restart."""
    lifecycle = LifecycleState()
    lifecycle.mark_database_healthy()
    lifecycle.mark_running()
    lifecycle.start_draining(reason="deploy")

    lifecycle.mark_running()

    snapshot = lifecycle.snapshot()
    assert snapshot.status is LifecycleStatus.DRAINING
    assert snapshot.database_status is DependencyHealthStatus.DRAINING
    assert snapshot.ready is False


def test_lifecycle_stopping_transition_rejects_healthy_dependency_readiness() -> None:
    """Healthy dependency reports stay draining while lifecycle is stopping."""
    lifecycle = LifecycleState()
    lifecycle.mark_running()
    lifecycle.mark_stopping()

    lifecycle.mark_redis_healthy()

    snapshot = lifecycle.snapshot()
    assert snapshot.status is LifecycleStatus.STOPPING
    assert snapshot.redis_status is DependencyHealthStatus.DRAINING
    assert snapshot.ready is False
