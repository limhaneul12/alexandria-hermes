"""Native Typer commands for Context Vault CLI operations."""

from __future__ import annotations

import typer
from app.cli_support.contracts.memory_command_contracts import (
    ContextCurateCommand,
    ContextIdCommand,
    ContextMemoryMapCommand,
    ContextRecallCommand,
    ContextReindexCommand,
)
from app.cli_support.handlers.context import (
    handle_context_chunks,
    handle_context_curate,
    handle_context_delete,
    handle_context_doctor_rag,
    handle_context_embed,
    handle_context_memory_map,
    handle_context_recall,
    handle_context_reindex,
)
from app.cli_support.typer_commands.typer_runtime import (
    run_client,
    run_context,
    run_local,
)
from app.memory.domain.event_enum.context_enums import (
    ContextKind,
    ContextScope,
    RagStrategy,
)

context_app = typer.Typer(help="Manage Context Vault entries")


def _recall_command(
    query: str,
    strategy: RagStrategy,
    limit: int,
    project: str | None,
    kind: ContextKind | None,
    include_scopes: list[ContextScope],
    workspace_id: str | None,
    agent_id: str | None,
    user_id: str | None,
    session_id: str | None,
) -> ContextRecallCommand:
    return ContextRecallCommand(
        query=query,
        strategy=strategy,
        limit=limit,
        project=project,
        kind=kind,
        include_scopes=include_scopes,
        workspace_id=workspace_id,
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
    )


@context_app.command("recall")
def context_recall(
    ctx: typer.Context,
    query: str,
    strategy: RagStrategy = typer.Option(RagStrategy.HYBRID, "--strategy"),
    limit: int = typer.Option(5, "--limit"),
    project: str | None = typer.Option(None, "--project"),
    kind: ContextKind | None = typer.Option(None, "--kind"),
    include: list[ContextScope] | None = typer.Option(None, "--include"),
    workspace_id: str | None = typer.Option(None, "--workspace-id"),
    agent_id: str | None = typer.Option(None, "--agent-id"),
    user_id: str | None = typer.Option(None, "--user-id"),
    session_id: str | None = typer.Option(None, "--session-id"),
) -> None:
    """Recall a Context Pack by query.

    Args:
        ctx: Typer context.
        query: Retrieval query.
        strategy: Retrieval strategy.
        limit: Maximum number of contexts.
        project: Optional project filter.
        kind: Optional context kind filter.

    Returns:
        None.
    """
    run_client(
        ctx,
        _recall_command(
            query,
            strategy,
            limit,
            project,
            kind,
            list(include or []),
            workspace_id,
            agent_id,
            user_id,
            session_id,
        ),
        handle_context_recall,
    )


@context_app.command("rag")
def context_rag(
    ctx: typer.Context,
    query: str,
    strategy: RagStrategy = typer.Option(RagStrategy.HYBRID, "--strategy"),
    limit: int = typer.Option(5, "--limit"),
    project: str | None = typer.Option(None, "--project"),
    kind: ContextKind | None = typer.Option(None, "--kind"),
    include: list[ContextScope] | None = typer.Option(None, "--include"),
    workspace_id: str | None = typer.Option(None, "--workspace-id"),
    agent_id: str | None = typer.Option(None, "--agent-id"),
    user_id: str | None = typer.Option(None, "--user-id"),
    session_id: str | None = typer.Option(None, "--session-id"),
) -> None:
    """Alias for context recall with RAG strategy controls.

    Args:
        ctx: Typer context.
        query: Retrieval query.
        strategy: Retrieval strategy.
        limit: Maximum number of contexts.
        project: Optional project filter.
        kind: Optional context kind filter.

    Returns:
        None.
    """
    run_client(
        ctx,
        _recall_command(
            query,
            strategy,
            limit,
            project,
            kind,
            list(include or []),
            workspace_id,
            agent_id,
            user_id,
            session_id,
        ),
        handle_context_recall,
    )


@context_app.command("chunks")
def context_chunks(ctx: typer.Context, context_id: str) -> None:
    """List chunks for one context.

    Args:
        ctx: Typer context.
        context_id: Context identifier.

    Returns:
        None.
    """
    run_client(ctx, ContextIdCommand(context_id=context_id), handle_context_chunks)


@context_app.command("delete")
def context_delete(ctx: typer.Context, context_id: str) -> None:
    """Hard delete one Context Vault entry.

    Args:
        ctx: Typer context.
        context_id: Context identifier.

    Returns:
        None.
    """
    run_client(ctx, ContextIdCommand(context_id=context_id), handle_context_delete)


@context_app.command("memory-map")
def context_memory_map(
    ctx: typer.Context,
    project: str | None = typer.Option(None, "--project"),
    limit: int = typer.Option(10, "--limit"),
    include_archived: bool = typer.Option(False, "--include-archived"),
) -> None:
    """Build a project memory map from stored contexts.

    Args:
        ctx: Typer context.
        project: Optional project filter.
        limit: Maximum contexts per backend page.
        include_archived: Whether archived contexts are included.

    Returns:
        None.
    """
    run_client(
        ctx,
        ContextMemoryMapCommand(
            project=project,
            limit=limit,
            include_archived=include_archived,
        ),
        handle_context_memory_map,
    )


@context_app.command("curate")
def context_curate(
    ctx: typer.Context,
    project: str | None = typer.Option(None, "--project"),
    stale_after_days: int = typer.Option(90, "--stale-after-days"),
    limit: int = typer.Option(50, "--limit"),
) -> None:
    """List stale or duplicate-looking memory curation candidates.

    Args:
        ctx: Typer context.
        project: Optional project filter.
        stale_after_days: Age threshold for stale candidate notes.
        limit: Maximum contexts to scan.

    Returns:
        None.
    """
    run_client(
        ctx,
        ContextCurateCommand(
            project=project,
            stale_after_days=stale_after_days,
            limit=limit,
        ),
        handle_context_curate,
    )


@context_app.command("embed")
def context_embed(ctx: typer.Context, context_id: str) -> None:
    """Report embedding support for a context.

    Args:
        ctx: Typer context.
        context_id: Context identifier.

    Returns:
        None.
    """
    run_local(ctx, ContextIdCommand(context_id=context_id), handle_context_embed)


@context_app.command("reindex")
def context_reindex(
    ctx: typer.Context,
    limit: int = typer.Option(100, "--limit", min=1, max=1000),
    force: bool = typer.Option(
        False,
        "--force",
        help="Rebuild active chunk embeddings even when model metadata already matches.",
    ),
) -> None:
    """Backfill or rebuild context chunk embeddings.

    Args:
        ctx: Typer context.
        limit: Maximum chunks to rebuild in this batch.
        force: Whether to rebuild active chunks even when model metadata matches.

    Returns:
        None.
    """
    run_client(
        ctx,
        ContextReindexCommand(limit=limit, force=force),
        handle_context_reindex,
    )


@context_app.command("doctor-rag")
def context_doctor_rag(ctx: typer.Context) -> None:
    """Check Context RAG dependency health.

    Args:
        ctx: Typer context.

    Returns:
        None.
    """
    run_context(ctx, handle_context_doctor_rag)
