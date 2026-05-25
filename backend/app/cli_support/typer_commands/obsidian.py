"""Native Typer commands for Obsidian integration."""

from __future__ import annotations

import typer
from app.cli_support.contracts.obsidian_command_contracts import (
    ObsidianAskCommand,
    ObsidianReadCommand,
    ObsidianSaveCommand,
    ObsidianSearchCommand,
)
from app.cli_support.handlers.obsidian import (
    handle_obsidian_ask,
    handle_obsidian_init,
    handle_obsidian_read,
    handle_obsidian_reindex,
    handle_obsidian_save,
    handle_obsidian_search,
    handle_obsidian_status,
)
from app.cli_support.typer_commands.typer_runtime import run_client, run_context
from app.obsidian.domain.event_enum.obsidian_enums import AlexandriaNoteType

obsidian_app = typer.Typer(help="Manage Obsidian-backed Alexandria vault")


@obsidian_app.command("status")
def obsidian_status(ctx: typer.Context) -> None:
    """Show Obsidian vault/index status.

    Args:
        ctx: Typer invocation context.
    """
    run_context(ctx, handle_obsidian_status)


@obsidian_app.command("init")
def obsidian_init(ctx: typer.Context) -> None:
    """Create Alexandria folders and START_HERE note.

    Args:
        ctx: Typer invocation context.
    """
    run_context(ctx, handle_obsidian_init)


@obsidian_app.command("reindex")
def obsidian_reindex(ctx: typer.Context) -> None:
    """Rebuild the Obsidian search index.

    Args:
        ctx: Typer invocation context.
    """
    run_context(ctx, handle_obsidian_reindex)


@obsidian_app.command("search")
def obsidian_search(
    ctx: typer.Context,
    query: str,
    limit: int = typer.Option(10, "--limit"),
    alexandria_type: AlexandriaNoteType | None = typer.Option(None, "--type"),
    project: str | None = typer.Option(None, "--project"),
    tag: list[str] | None = typer.Option(None, "--tag"),
) -> None:
    """Search Alexandria-managed Obsidian notes.

    Args:
        ctx: Typer invocation context.
        query: Search text.
        limit: Maximum hit count.
        alexandria_type: Optional note type filter.
        project: Optional project filter.
        tag: Optional tag filters.
    """
    run_client(
        ctx,
        ObsidianSearchCommand(
            query=query,
            limit=limit,
            alexandria_type=alexandria_type,
            project=project,
            tags=list(tag or []),
        ),
        handle_obsidian_search,
    )


@obsidian_app.command("read")
def obsidian_read(
    ctx: typer.Context,
    note_id: str | None = typer.Argument(None),
    path: str | None = typer.Option(None, "--path"),
) -> None:
    """Read one note by id or --path.

    Args:
        ctx: Typer invocation context.
        note_id: Optional stable note id.
        path: Optional vault-relative Markdown path.
    """
    run_client(
        ctx,
        ObsidianReadCommand(note_id=note_id, path=path),
        handle_obsidian_read,
    )


@obsidian_app.command("save")
def obsidian_save(
    ctx: typer.Context,
    title: str,
    body_file: str = typer.Option(..., "--body-file"),
    alexandria_type: AlexandriaNoteType = typer.Option(..., "--type"),
    note_id: str | None = typer.Option(None, "--id"),
    path: str | None = typer.Option(None, "--path"),
    project: str | None = typer.Option(None, "--project"),
    tag: list[str] | None = typer.Option(None, "--tag"),
) -> None:
    """Save one note from a Markdown body file.

    Args:
        ctx: Typer invocation context.
        title: Note title.
        body_file: Markdown body file path.
        alexandria_type: Alexandria note type.
        note_id: Optional stable note id.
        path: Optional vault-relative path.
        project: Optional project metadata.
        tag: Optional tag metadata.
    """
    run_client(
        ctx,
        ObsidianSaveCommand(
            title=title,
            body_file=body_file,
            alexandria_type=alexandria_type,
            note_id=note_id,
            path=path,
            project=project,
            tags=list(tag or []),
        ),
        handle_obsidian_save,
    )


@obsidian_app.command("ask")
def obsidian_ask(
    ctx: typer.Context,
    query: str,
    active_note_path: str | None = typer.Option(None, "--active-note-path"),
    selection: str | None = typer.Option(None, "--selection"),
    project: str | None = typer.Option(None, "--project"),
    save_transcript: bool = typer.Option(False, "--save-transcript"),
) -> None:
    """Ask the Obsidian-aware Alexandria librarian.

    Args:
        ctx: Typer invocation context.
        query: Question for the librarian.
        active_note_path: Optional active Obsidian note path.
        selection: Optional selected text from Obsidian.
        project: Optional project filter.
        save_transcript: Whether to write the chat transcript note.
    """
    run_client(
        ctx,
        ObsidianAskCommand(
            query=query,
            active_note_path=active_note_path,
            selection=selection,
            project=project,
            save_transcript=save_transcript,
        ),
        handle_obsidian_ask,
    )
