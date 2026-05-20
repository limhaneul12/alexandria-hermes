"""Native Typer commands for durable Memory Compact artifacts."""

from __future__ import annotations

import typer
from app.cli_support.contracts.memory_command_contracts import (
    MemoryCompactIdCommand,
    MemoryCompactListCommand,
)
from app.cli_support.handlers.memory_compact import (
    handle_memory_compact_current,
    handle_memory_compact_get,
    handle_memory_compact_list,
)
from app.cli_support.typer_commands.typer_runtime import run_client
from app.memory.domain.event_enum.memory_compact_enums import (
    MemoryCompactStatus,
)

memory_compact_app = typer.Typer(help="Browse durable Memory Compact artifacts")


@memory_compact_app.command("list")
def memory_compact_list(
    ctx: typer.Context,
    project: str | None = typer.Option(None, "--project"),
    status: MemoryCompactStatus | None = typer.Option(None, "--status"),
    limit: int = typer.Option(20, "--limit"),
    offset: int = typer.Option(0, "--offset"),
) -> None:
    """List durable Memory Compact artifacts.

    Args:
        ctx: Typer command context.
        project: Optional project filter.
        status: Optional lifecycle status filter.
        limit: Maximum number of rows to return.
        offset: Number of rows to skip.
    """
    run_client(
        ctx,
        MemoryCompactListCommand(
            project=project,
            status=status,
            limit=limit,
            offset=offset,
        ),
        handle_memory_compact_list,
    )


@memory_compact_app.command("current")
def memory_compact_current(
    ctx: typer.Context,
    project: str | None = typer.Option(None, "--project"),
) -> None:
    """Read the current Memory Compact for a project.

    Args:
        ctx: Typer command context.
        project: Optional project filter.
    """
    run_client(
        ctx,
        MemoryCompactListCommand(
            project=project,
            status=MemoryCompactStatus.CURRENT,
            limit=1,
            offset=0,
        ),
        handle_memory_compact_current,
    )


@memory_compact_app.command("get")
def memory_compact_get(ctx: typer.Context, compact_id: str) -> None:
    """Read one selected Memory Compact by id.

    Args:
        ctx: Typer command context.
        compact_id: Memory Compact identifier.
    """
    run_client(
        ctx,
        MemoryCompactIdCommand(compact_id=compact_id),
        handle_memory_compact_get,
    )
