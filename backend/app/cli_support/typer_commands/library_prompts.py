"""Native Typer commands for prompt-oriented CLI groups."""

from __future__ import annotations

import typer
from app.cli_support.contracts.command_contracts import (
    ItemIdCommand,
    PromptDeprecateCommand,
    PromptDiffCommand,
    PromptsListCommand,
    PromptsSearchCommand,
    PromptsUseCommand,
    PromptVersionCommand,
)
from app.cli_support.handlers.prompts import (
    handle_prompts_deprecate,
    handle_prompts_diff,
    handle_prompts_get,
    handle_prompts_list,
    handle_prompts_search,
    handle_prompts_use,
    handle_prompts_version,
)
from app.cli_support.typer_commands.command_choices import PromptKind
from app.cli_support.typer_commands.typer_runtime import run_client, values

prompts_app = typer.Typer(help="Manage prompt records")


@prompts_app.command("list")
def prompts_list(
    ctx: typer.Context,
    limit: int = typer.Option(20, "--limit"),
    offset: int = typer.Option(0, "--offset"),
    kind: PromptKind | None = typer.Option(None, "--kind"),
    tag: str | None = typer.Option(None, "--tag"),
) -> None:
    """List registered prompts.

    Args:
        ctx: Typer context.
        limit: Maximum number of prompts.
        offset: Result offset.
        kind: Optional prompt kind filter.
        tag: Optional tag filter.

    Returns:
        None.
    """
    run_client(
        ctx,
        PromptsListCommand(limit=limit, offset=offset, kind=kind, tag=tag),
        handle_prompts_list,
    )


@prompts_app.command("get")
def prompts_get(ctx: typer.Context, item_id: str) -> None:
    """Read one prompt.

    Args:
        ctx: Typer context.
        item_id: Prompt identifier.

    Returns:
        None.
    """
    run_client(ctx, ItemIdCommand(item_id=item_id), handle_prompts_get)


@prompts_app.command("search")
def prompts_search(
    ctx: typer.Context,
    query: str,
    limit: int = typer.Option(20, "--limit"),
    offset: int = typer.Option(0, "--offset"),
    kind: PromptKind | None = typer.Option(None, "--kind"),
    tag: list[str] | None = typer.Option(None, "--tag"),
) -> None:
    """Search prompt records by text.

    Args:
        ctx: Typer context.
        query: Search text.
        limit: Maximum result count.
        offset: Result offset.
        kind: Optional prompt kind filter.
        tag: Repeatable tag filter.

    Returns:
        None.
    """
    run_client(
        ctx,
        PromptsSearchCommand(
            query=query,
            limit=limit,
            offset=offset,
            kind=kind,
            tag=values(tag),
        ),
        handle_prompts_search,
    )


@prompts_app.command("version")
def prompts_version(
    ctx: typer.Context,
    item_id: str,
    version: str = typer.Option(..., "--version"),
    change_summary: str | None = typer.Option(None, "--change-summary"),
) -> None:
    """Update a prompt version.

    Args:
        ctx: Typer context.
        item_id: Prompt identifier.
        version: New prompt version.
        change_summary: Optional change summary.

    Returns:
        None.
    """
    run_client(
        ctx,
        PromptVersionCommand(
            item_id=item_id,
            version=version,
            change_summary=change_summary,
        ),
        handle_prompts_version,
    )


@prompts_app.command("deprecate")
def prompts_deprecate(
    ctx: typer.Context,
    item_id: str,
    reason: str | None = typer.Option(None, "--reason"),
) -> None:
    """Mark a prompt deprecated.

    Args:
        ctx: Typer context.
        item_id: Prompt identifier.
        reason: Optional deprecation reason.

    Returns:
        None.
    """
    run_client(
        ctx,
        PromptDeprecateCommand(item_id=item_id, reason=reason),
        handle_prompts_deprecate,
    )


@prompts_app.command("diff")
def prompts_diff(ctx: typer.Context, left_item_id: str, right_item_id: str) -> None:
    """Print a unified diff between two prompt records.

    Args:
        ctx: Typer context.
        left_item_id: Base prompt id.
        right_item_id: Comparison prompt id.

    Returns:
        None.
    """
    run_client(
        ctx,
        PromptDiffCommand(left_item_id=left_item_id, right_item_id=right_item_id),
        handle_prompts_diff,
    )


@prompts_app.command("use")
def prompts_use(
    ctx: typer.Context,
    item_id: str,
    actor_id: str | None = typer.Option(None, "--actor-id"),
    actor_name: str = typer.Option("Hermes CLI", "--actor-name"),
) -> None:
    """Print a prompt and record usage.

    Args:
        ctx: Typer context.
        item_id: Prompt identifier.
        actor_id: Optional actor identifier.
        actor_name: Actor display name.

    Returns:
        None.
    """
    run_client(
        ctx,
        PromptsUseCommand(
            item_id=item_id,
            actor_id=actor_id,
            actor_name=actor_name,
        ),
        handle_prompts_use,
    )
