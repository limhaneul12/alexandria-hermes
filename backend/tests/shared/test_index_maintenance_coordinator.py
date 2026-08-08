"""Shared index maintenance serialization contracts."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import anyio
import pytest
from app.shared.application.index_maintenance_coordinator import (
    IndexMaintenanceCoordinator,
)
from app.shared.exceptions.common_exceptions import IndexMaintenanceConflictError


class _RecordingProcessLock:
    def __init__(self) -> None:
        self.calls: list[tuple[bool, bool]] = []

    @asynccontextmanager
    async def operation(self, *, wait: bool, shared: bool) -> AsyncIterator[None]:
        self.calls.append((wait, shared))
        yield


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


def test_postgres_mode_allows_independent_short_writes_to_overlap() -> None:
    """Compatible short writers should not be globally serialized on PostgreSQL."""

    async def scenario() -> tuple[int, list[str]]:
        coordinator = IndexMaintenanceCoordinator(allow_concurrent_writes=True)
        first_entered = anyio.Event()
        second_entered = anyio.Event()
        release = anyio.Event()
        active = 0
        peak_active = 0
        events: list[str] = []

        async def writer(name: str, entered: anyio.Event) -> None:
            nonlocal active, peak_active
            async with coordinator.write_operation(name):
                active += 1
                peak_active = max(peak_active, active)
                events.append(f"{name}-entered")
                entered.set()
                await release.wait()
                active -= 1
                events.append(f"{name}-released")

        async with anyio.create_task_group() as group:
            group.start_soon(writer, "writer-a", first_entered)
            group.start_soon(writer, "writer-b", second_entered)
            await first_entered.wait()
            await second_entered.wait()
            release.set()

        return peak_active, events

    peak_active, events = anyio.run(scenario)

    assert peak_active == 2
    assert {event for event in events if event.endswith("-entered")} == {
        "writer-a-entered",
        "writer-b-entered",
    }


def test_waiting_maintenance_prevents_new_writer_starvation() -> None:
    """Once maintenance queues, later writers should wait behind it."""

    async def scenario() -> list[str]:
        coordinator = IndexMaintenanceCoordinator(allow_concurrent_writes=True)
        first_writer_entered = anyio.Event()
        release_first_writer = anyio.Event()
        maintenance_entered = anyio.Event()
        release_maintenance = anyio.Event()
        later_writer_entered = anyio.Event()
        events: list[str] = []

        async def first_writer() -> None:
            async with coordinator.write_operation("writer-a"):
                events.append("writer-a-entered")
                first_writer_entered.set()
                await release_first_writer.wait()
                events.append("writer-a-released")

        async def maintenance() -> None:
            await first_writer_entered.wait()
            async with coordinator.operation("vault-reindex", wait=True):
                events.append("maintenance-entered")
                maintenance_entered.set()
                await release_maintenance.wait()
                events.append("maintenance-released")

        async def later_writer() -> None:
            await first_writer_entered.wait()
            await anyio.sleep(0)
            async with coordinator.write_operation("writer-b"):
                events.append("writer-b-entered")
                later_writer_entered.set()

        async with anyio.create_task_group() as group:
            group.start_soon(first_writer)
            group.start_soon(maintenance)
            await first_writer_entered.wait()
            await anyio.sleep(0)
            group.start_soon(later_writer)
            with anyio.move_on_after(0.05):
                await later_writer_entered.wait()
            assert not later_writer_entered.is_set()
            release_first_writer.set()
            await maintenance_entered.wait()
            with anyio.move_on_after(0.05):
                await later_writer_entered.wait()
            assert not later_writer_entered.is_set()
            release_maintenance.set()

        return events

    events = anyio.run(scenario)

    assert events == [
        "writer-a-entered",
        "writer-a-released",
        "maintenance-entered",
        "maintenance-released",
        "writer-b-entered",
    ]


def test_shared_writer_cannot_upgrade_to_exclusive_maintenance() -> None:
    """A nested maintenance step must enter through an exclusive outer operation."""

    async def scenario() -> str:
        coordinator = IndexMaintenanceCoordinator(allow_concurrent_writes=True)
        async with coordinator.write_operation("note-write"):
            with pytest.raises(RuntimeError) as exc_info:
                async with coordinator.operation("vault-reindex", wait=True):
                    raise AssertionError("shared lease unexpectedly upgraded")
        return str(exc_info.value)

    error = anyio.run(scenario)

    assert "cannot upgrade from shared to exclusive" in error


def test_process_lock_receives_shared_and_exclusive_modes() -> None:
    """The coordinator should propagate the narrowest cross-process lock mode."""

    async def scenario() -> list[tuple[bool, bool]]:
        process_lock = _RecordingProcessLock()
        coordinator = IndexMaintenanceCoordinator(
            process_lock=process_lock,
            allow_concurrent_writes=True,
        )
        async with coordinator.write_operation("note-write"):
            pass
        async with coordinator.operation("vault-reindex", wait=False):
            pass
        return process_lock.calls

    calls = anyio.run(scenario)

    assert calls == [(True, True), (False, False)]
