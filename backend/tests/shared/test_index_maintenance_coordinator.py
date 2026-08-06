"""Shared index maintenance serialization contracts."""

from __future__ import annotations

import anyio
import pytest
from app.shared.application.index_maintenance_coordinator import (
    IndexMaintenanceCoordinator,
)
from app.shared.exceptions.common_exceptions import IndexMaintenanceConflictError
from app.shared.infrastructure.interprocess_file_lock import InterprocessFileLock


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


def test_write_operation_waits_until_active_maintenance_releases() -> None:
    """Canonical writes queue instead of racing an active maintenance writer."""

    async def scenario() -> list[str]:
        coordinator = IndexMaintenanceCoordinator()
        maintenance_entered = anyio.Event()
        release_maintenance = anyio.Event()
        write_entered = anyio.Event()
        events: list[str] = []

        async def maintenance() -> None:
            async with coordinator.operation("vault_reindex"):
                events.append("maintenance-entered")
                maintenance_entered.set()
                await release_maintenance.wait()
                events.append("maintenance-released")

        async def writer() -> None:
            await maintenance_entered.wait()
            async with coordinator.write_operation("obsidian_note_write"):
                events.append("write-entered")
                write_entered.set()

        async with anyio.create_task_group() as group:
            group.start_soon(maintenance)
            group.start_soon(writer)
            await maintenance_entered.wait()
            with anyio.move_on_after(0.05):
                await write_entered.wait()
            assert not write_entered.is_set()
            release_maintenance.set()

        return events

    events = anyio.run(scenario)

    assert events == [
        "maintenance-entered",
        "maintenance-released",
        "write-entered",
    ]


def test_separate_coordinators_share_one_interprocess_write_lane(tmp_path) -> None:
    """Two application processes must coordinate through the same lock path."""

    async def scenario() -> tuple[str, list[str]]:
        lock_path = tmp_path / "alexandria.db.index-write.lock"
        first = IndexMaintenanceCoordinator(
            process_lock=InterprocessFileLock(lock_path)
        )
        second = IndexMaintenanceCoordinator(
            process_lock=InterprocessFileLock(lock_path)
        )
        entered = anyio.Event()
        release = anyio.Event()
        queued_entered = anyio.Event()
        events: list[str] = []
        conflict = ""

        async def owner() -> None:
            async with first.operation("vault_reindex"):
                events.append("owner-entered")
                entered.set()
                await release.wait()
                events.append("owner-released")

        async def queued_writer() -> None:
            await entered.wait()
            async with second.write_operation("obsidian_note_write"):
                events.append("queued-entered")
                queued_entered.set()

        async def fail_fast_maintenance() -> None:
            nonlocal conflict
            await entered.wait()
            with pytest.raises(IndexMaintenanceConflictError) as exc_info:
                async with second.operation("graph_rebuild"):
                    raise AssertionError("external process lease was not enforced")
            conflict = str(exc_info.value)

        async with anyio.create_task_group() as group:
            group.start_soon(owner)
            await entered.wait()
            group.start_soon(fail_fast_maintenance)
            group.start_soon(queued_writer)
            with anyio.move_on_after(0.05):
                await queued_entered.wait()
            assert not queued_entered.is_set()
            release.set()

        return conflict, events

    conflict, events = anyio.run(scenario)

    assert "another process owns" in conflict
    assert events == ["owner-entered", "owner-released", "queued-entered"]
