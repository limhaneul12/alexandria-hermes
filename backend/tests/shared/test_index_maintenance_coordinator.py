"""Shared index maintenance serialization contracts."""

from __future__ import annotations

import anyio
import pytest
from app.shared.application.index_maintenance_coordinator import (
    IndexMaintenanceCoordinator,
)
from app.shared.exceptions.common_exceptions import IndexMaintenanceConflictError


def test_coordinator_is_reentrant_for_one_task_and_rejects_parallel_work() -> None:
    """Nested work may proceed, while a second operation fails fast."""

    async def scenario() -> tuple[str, str]:
        coordinator = IndexMaintenanceCoordinator()
        entered = anyio.Event()
        release = anyio.Event()
        conflict = ""

        async def first() -> None:
            async with (
                coordinator.operation("vault_reindex"),
                coordinator.operation("embedding_reindex"),
            ):
                entered.set()
                await release.wait()

        async def second() -> None:
            nonlocal conflict
            await entered.wait()
            with pytest.raises(IndexMaintenanceConflictError) as exc_info:
                async with coordinator.operation("graph_rebuild"):
                    raise AssertionError("parallel maintenance unexpectedly entered")
            conflict = str(exc_info.value)
            release.set()

        async with anyio.create_task_group() as group:
            group.start_soon(first)
            group.start_soon(second)
        return conflict, coordinator.active_operation or ""

    conflict, active = anyio.run(scenario)

    assert "vault_reindex" in conflict
    assert "graph_rebuild" in conflict
    assert active == ""
