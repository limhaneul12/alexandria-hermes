"""Native Typer commands for Obsidian integration."""

from __future__ import annotations

import typer
from app.cli_support.contracts.obsidian_command_contracts import (
    ObsidianAskCommand,
    ObsidianCaptureCommand,
    ObsidianReadCommand,
    ObsidianRelatedCommand,
    ObsidianSaveCommand,
    ObsidianSearchCommand,
)
from app.cli_support.handlers.obsidian import (
    handle_obsidian_ask,
    handle_obsidian_capture,
    handle_obsidian_init,
    handle_obsidian_read,
    handle_obsidian_reindex,
    handle_obsidian_related,
    handle_obsidian_save,
    handle_obsidian_search,
    handle_obsidian_status,
)
from app.cli_support.obsidian_plugin_install import install_local_obsidian_plugin
from app.cli_support.presentation.output_renderers import print_json
from app.cli_support.typer_commands.typer_runtime import (
    command_context,
    run_client,
    run_context,
)
from app.obsidian.domain.event_enum.obsidian_enums import AlexandriaNoteType

obsidian_app = typer.Typer(help="Manage Obsidian-backed Alexandria vault")


@obsidian_app.command("install-local")
def obsidian_install_local(
    ctx: typer.Context,
    vault_path: str = typer.Option(..., "--vault-path"),
    plugin_install_mode: str = typer.Option("copy", "--plugin-install-mode"),
    enable_plugin: bool = typer.Option(True, "--enable-plugin/--no-enable-plugin"),
) -> None:
    """Install the local Alexandria Obsidian plugin into a vault.

    Args:
        ctx: Typer invocation context.
        vault_path: Target Obsidian vault path.
        plugin_install_mode: copy or symlink. Copy avoids repo data.json writes.
        enable_plugin: Whether to add the plugin id to community-plugins.json.
    """
    context = command_context(ctx)
    try:
        result = install_local_obsidian_plugin(
            vault_path=vault_path,
            install_mode=plugin_install_mode,
            enable_plugin=enable_plugin,
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=context.stderr)
        raise typer.Exit(1) from exc
    print_json(result.to_payload(), context.stdout)


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


@obsidian_app.command("related")
def obsidian_related(
    ctx: typer.Context,
    note_id: str | None = typer.Argument(None),
    path: str | None = typer.Option(None, "--path"),
    limit: int = typer.Option(10, "--limit"),
) -> None:
    """Read graph-related notes by id or --path.

    Args:
        ctx: Typer invocation context.
        note_id: Optional stable note id.
        path: Optional vault-relative Markdown path.
        limit: Maximum related notes.
    """
    run_client(
        ctx,
        ObsidianRelatedCommand(note_id=note_id, path=path, limit=limit),
        handle_obsidian_related,
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
    status: str = typer.Option("active", "--status"),
    source: str = typer.Option("cli", "--source"),
    frontmatter_json: str | None = typer.Option(None, "--frontmatter-json"),
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
        status: Frontmatter lifecycle status.
        source: Frontmatter source marker.
        frontmatter_json: Extra JSON object merged into frontmatter.
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
            status=status,
            source=source,
            frontmatter_json=frontmatter_json,
            tags=list(tag or []),
        ),
        handle_obsidian_save,
    )


@obsidian_app.command("capture")
def obsidian_capture(
    ctx: typer.Context,
    title: str,
    body_file: str = typer.Option(..., "--body-file"),
    alexandria_type: AlexandriaNoteType = typer.Option(..., "--type"),
    note_id: str | None = typer.Option(None, "--id"),
    path: str | None = typer.Option(None, "--path"),
    project: str | None = typer.Option(None, "--project"),
    status: str = typer.Option("draft", "--status"),
    source: str = typer.Option("import", "--source"),
    frontmatter_json: str | None = typer.Option(None, "--frontmatter-json"),
    covered_from: str | None = typer.Option(None, "--covered-from"),
    covered_to: str | None = typer.Option(None, "--covered-to"),
    prompt_kind: str | None = typer.Option(None, "--prompt-kind"),
    tag: list[str] | None = typer.Option(None, "--tag"),
) -> None:
    """Capture a canonical memory compact, skill draft, or prompt note.

    Args:
        ctx: Typer invocation context.
        title: Artifact title.
        body_file: Markdown body file path.
        alexandria_type: Artifact note type; memory_compact, skill, or prompt.
        note_id: Optional stable note id.
        path: Optional vault-relative path.
        project: Optional project metadata.
        status: Frontmatter lifecycle status.
        source: Frontmatter source marker.
        frontmatter_json: Extra JSON object merged into frontmatter.
        covered_from: Optional compact coverage start timestamp.
        covered_to: Optional compact coverage end timestamp.
        prompt_kind: Optional prompt kind; defaults to template for prompts.
        tag: Optional extra tags.
    """
    run_client(
        ctx,
        ObsidianCaptureCommand(
            title=title,
            body_file=body_file,
            alexandria_type=alexandria_type,
            note_id=note_id,
            path=path,
            project=project,
            status=status,
            source=source,
            frontmatter_json=frontmatter_json,
            covered_from=covered_from,
            covered_to=covered_to,
            prompt_kind=prompt_kind,
            tags=list(tag or []),
        ),
        handle_obsidian_capture,
    )


@obsidian_app.command("ask")
def obsidian_ask(
    ctx: typer.Context,
    query: str,
    active_note_path: str | None = typer.Option(None, "--active-note-path"),
    selection: str | None = typer.Option(None, "--selection"),
    project: str | None = typer.Option(None, "--project"),
    save_transcript: bool = typer.Option(False, "--save-transcript"),
    delegate_to_librarian: bool = typer.Option(False, "--delegate"),
    provider_id: str | None = typer.Option(None, "--provider-id"),
    profile_id: str | None = typer.Option(None, "--profile-id"),
) -> None:
    """Ask the Obsidian-aware Alexandria librarian.

    Args:
        ctx: Typer invocation context.
        query: Question for the librarian.
        active_note_path: Optional active Obsidian note path.
        selection: Optional selected text from Obsidian.
        project: Optional project filter.
        save_transcript: Whether to write the chat transcript note.
        delegate_to_librarian: Whether to request provider delegation hooks.
        provider_id: Optional preferred provider id.
        profile_id: Optional preferred librarian profile id.
    """
    run_client(
        ctx,
        ObsidianAskCommand(
            query=query,
            active_note_path=active_note_path,
            selection=selection,
            project=project,
            save_transcript=save_transcript,
            delegate_to_librarian=delegate_to_librarian,
            provider_id=provider_id,
            profile_id=profile_id,
        ),
        handle_obsidian_ask,
    )
