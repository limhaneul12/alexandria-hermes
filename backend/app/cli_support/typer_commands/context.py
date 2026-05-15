"""Native Typer commands for Context Vault CLI operations."""

from __future__ import annotations

import typer
from app.cli_support.contracts.command_contracts import (
    ContextIdCommand,
    ContextLintCommand,
    ContextMetadataCommand,
    ContextRecallCommand,
    ContextSaveCommand,
    NoArgsCommand,
)
from app.cli_support.handlers.context import (
    handle_context_chunks,
    handle_context_doctor_rag,
    handle_context_embed,
    handle_context_lint,
    handle_context_recall,
    handle_context_reindex,
    handle_context_save,
)
from app.cli_support.typer_commands.typer_runtime import (
    run_client,
    run_context,
    run_local,
    values,
)
from app.library.domain.event_enum.context_enums import (
    ContextImportance,
    ContextKind,
    ContextSourceType,
    RagStrategy,
)

context_app = typer.Typer(help="Manage Context Vault entries")


def _metadata(
    title: str,
    kind: ContextKind,
    summary: str | None,
    project: str | None,
    source_agent: str,
    tag: list[str] | None,
) -> ContextMetadataCommand:
    return ContextMetadataCommand(
        title=title,
        kind=kind,
        summary=summary,
        project=project,
        source_agent=source_agent,
        tag=values(tag),
    )


@context_app.command("lint")
def context_lint(
    ctx: typer.Context,
    content_file: str,
    title: str = typer.Option(..., "--title"),
    kind: ContextKind = typer.Option(ContextKind.HANDOFF, "--kind"),
    summary: str | None = typer.Option(None, "--summary"),
    project: str | None = typer.Option(None, "--project"),
    source_agent: str = typer.Option("Hermes", "--source-agent"),
    tag: list[str] | None = typer.Option(None, "--tag"),
) -> None:
    """Lint context Markdown.

    Args:
        ctx: Typer context.
        content_file: Markdown file path.
        title: Context title.
        kind: Context kind.
        summary: Optional summary.
        project: Optional project name.
        source_agent: Agent creating the context.
        tag: Repeatable context tags.

    Returns:
        None.
    """
    metadata = _metadata(title, kind, summary, project, source_agent, tag)
    run_client(
        ctx,
        ContextLintCommand(
            title=metadata.title,
            kind=metadata.kind,
            summary=metadata.summary,
            project=metadata.project,
            source_agent=metadata.source_agent,
            tag=metadata.tag,
            content_file=content_file,
        ),
        handle_context_lint,
    )


@context_app.command("save")
def context_save(
    ctx: typer.Context,
    content: str | None = typer.Option(None, "--content"),
    content_file: str | None = typer.Option(None, "--content-file"),
    title: str = typer.Option(..., "--title"),
    kind: ContextKind = typer.Option(ContextKind.HANDOFF, "--kind"),
    summary: str | None = typer.Option(None, "--summary"),
    project: str | None = typer.Option(None, "--project"),
    source_agent: str = typer.Option("Hermes", "--source-agent"),
    tag: list[str] | None = typer.Option(None, "--tag"),
    source_type: ContextSourceType = typer.Option(
        ContextSourceType.AGENT,
        "--source-type",
    ),
    importance: ContextImportance = typer.Option(
        ContextImportance.MEDIUM,
        "--importance",
    ),
) -> None:
    """Save context Markdown.

    Args:
        ctx: Typer context.
        content: Inline Markdown content.
        content_file: Markdown file path.
        title: Context title.
        kind: Context kind.
        summary: Optional summary.
        project: Optional project name.
        source_agent: Agent creating the context.
        tag: Repeatable context tags.
        source_type: Context source type.
        importance: Context importance.

    Returns:
        None.
    """
    metadata = _metadata(title, kind, summary, project, source_agent, tag)
    run_client(
        ctx,
        ContextSaveCommand(
            title=metadata.title,
            kind=metadata.kind,
            summary=metadata.summary,
            project=metadata.project,
            source_agent=metadata.source_agent,
            tag=metadata.tag,
            content=content,
            content_file=content_file,
            source_type=source_type,
            importance=importance,
        ),
        handle_context_save,
    )


def _recall_command(
    query: str,
    strategy: RagStrategy,
    limit: int,
    project: str | None,
    kind: ContextKind | None,
) -> ContextRecallCommand:
    return ContextRecallCommand(
        query=query,
        strategy=strategy,
        limit=limit,
        project=project,
        kind=kind,
    )


@context_app.command("recall")
def context_recall(
    ctx: typer.Context,
    query: str,
    strategy: RagStrategy = typer.Option(RagStrategy.HYBRID, "--strategy"),
    limit: int = typer.Option(5, "--limit"),
    project: str | None = typer.Option(None, "--project"),
    kind: ContextKind | None = typer.Option(None, "--kind"),
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
        _recall_command(query, strategy, limit, project, kind),
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
        _recall_command(query, strategy, limit, project, kind),
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
def context_reindex(ctx: typer.Context) -> None:
    """Report context reindex support.

    Args:
        ctx: Typer context.

    Returns:
        None.
    """
    run_local(ctx, NoArgsCommand(), handle_context_reindex)


@context_app.command("doctor-rag")
def context_doctor_rag(ctx: typer.Context) -> None:
    """Check Context RAG dependency health.

    Args:
        ctx: Typer context.

    Returns:
        None.
    """
    run_context(ctx, handle_context_doctor_rag)
