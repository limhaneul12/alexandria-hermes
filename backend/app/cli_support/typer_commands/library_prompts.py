"""Native Typer commands for prompt-oriented CLI groups."""

from __future__ import annotations

import typer
from app.cli_support.contracts.command_contracts import (
    ItemIdCommand,
    PromptDeprecateCommand,
    PromptDiffCommand,
    PromptsCreateCommand,
    PromptsListCommand,
    PromptsSearchCommand,
    PromptsUseCommand,
    PromptVersionCommand,
)
from app.cli_support.handlers.prompts import (
    handle_prompts_create,
    handle_prompts_deprecate,
    handle_prompts_diff,
    handle_prompts_get,
    handle_prompts_list,
    handle_prompts_search,
    handle_prompts_use,
    handle_prompts_version,
)
from app.cli_support.typer_commands.command_choices import (
    PromptContentFormat,
    PromptCreatorType,
    PromptDomain,
    PromptKind,
    PromptSourceType,
    PromptTaskType,
)
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
) -> None:
    """Search prompt records by text.

    Args:
        ctx: Typer context.
        query: Search text.
        limit: Maximum result count.
        offset: Result offset.

    Returns:
        None.
    """
    run_client(
        ctx,
        PromptsSearchCommand(query=query, limit=limit, offset=offset),
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


@prompts_app.command("create")
def prompts_create(
    ctx: typer.Context,
    title: str = typer.Option(..., "--title"),
    summary: str | None = typer.Option(None, "--summary"),
    content: str | None = typer.Option(None, "--content"),
    content_file: str | None = typer.Option(None, "--content-file"),
    kind: PromptKind = typer.Option(PromptKind.USER_TEMPLATE, "--kind"),
    domain: PromptDomain = typer.Option(PromptDomain.GENERAL, "--domain"),
    task_type: PromptTaskType = typer.Option(
        PromptTaskType.GENERAL_TASK,
        "--task-type",
    ),
    content_format: PromptContentFormat = typer.Option(
        PromptContentFormat.MARKDOWN,
        "--format",
    ),
    var: list[str] | None = typer.Option(None, "--var"),
    output_format: str | None = typer.Option(None, "--output-format"),
    target_actor: str | None = typer.Option(None, "--target-actor"),
    target_model_family: str | None = typer.Option(None, "--target-model-family"),
    language: str | None = typer.Option(None, "--language"),
    related_item_id: list[str] | None = typer.Option(None, "--related-item-id"),
    category_id: str | None = typer.Option(None, "--category-id"),
    tag: list[str] | None = typer.Option(None, "--tag"),
    version: str = typer.Option("1.0.0", "--version"),
    created_by: str = typer.Option("Hermes CLI", "--created-by"),
    created_by_type: PromptCreatorType = typer.Option(
        PromptCreatorType.USER,
        "--created-by-type",
    ),
    source_type: PromptSourceType = typer.Option(
        PromptSourceType.USER_CREATED,
        "--source-type",
    ),
    active: bool = typer.Option(False, "--active"),
) -> None:
    """Create a prompt.

    Args:
        ctx: Typer context.
        title: Prompt title.
        summary: Optional prompt summary.
        content: Inline prompt content.
        content_file: File containing prompt content.
        kind: Prompt kind.
        domain: Prompt domain.
        task_type: Prompt task type.
        content_format: Prompt content format.
        var: Repeatable prompt variables.
        output_format: Optional output format.
        target_actor: Optional target actor.
        target_model_family: Optional target model family.
        language: Optional language.
        related_item_id: Repeatable related item identifiers.
        category_id: Optional category identifier.
        tag: Repeatable tags.
        version: Prompt version.
        created_by: Creator display name.
        created_by_type: Creator type.
        source_type: Source type.
        active: Whether the prompt is active.

    Returns:
        None.
    """
    run_client(
        ctx,
        PromptsCreateCommand(
            title=title,
            summary=summary,
            content=content,
            content_file=content_file,
            kind=kind,
            domain=domain,
            task_type=task_type,
            content_format=content_format,
            var=values(var),
            output_format=output_format,
            target_actor=target_actor,
            target_model_family=target_model_family,
            language=language,
            related_item_id=values(related_item_id),
            category_id=category_id,
            tag=values(tag),
            version=version,
            created_by=created_by,
            created_by_type=created_by_type,
            source_type=source_type,
            active=active,
        ),
        handle_prompts_create,
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
