"""Native Typer commands for library-oriented CLI groups."""

from __future__ import annotations

import typer
from app.cli_support.contracts.command_contracts import (
    FolderIdCommand,
    FoldersCreateCommand,
    FoldersEnsureCommand,
    FoldersListCommand,
    ItemIdCommand,
    LibraryListCommand,
    LibrarySearchCommand,
    MinioCommand,
    SkillsCreateCommand,
    SkillsListCommand,
    SkillsSearchCommand,
)
from app.cli_support.handlers.library import (
    handle_folders_create,
    handle_folders_delete,
    handle_folders_ensure,
    handle_folders_list,
    handle_library_list,
    handle_library_search,
    handle_minio_import,
    handle_minio_scan,
    handle_skills_create,
    handle_skills_delete,
    handle_skills_get,
    handle_skills_list,
    handle_skills_search,
)
from app.cli_support.typer_commands.command_choices import (
    LibraryItemType,
    SkillRiskLevel,
)
from app.cli_support.typer_commands.typer_runtime import run_client, values

skills_app = typer.Typer(help="Manage skill records")
folders_app = typer.Typer(help="Manage library folders")
library_app = typer.Typer(help="Browse library items")
minio_app = typer.Typer(help="Sync external MINIO archive")


@skills_app.command("list")
def skills_list(
    ctx: typer.Context,
    limit: int = typer.Option(20, "--limit"),
    offset: int = typer.Option(0, "--offset"),
) -> None:
    """List registered skills.

    Args:
        ctx: Typer context.
        limit: Maximum number of skills.
        offset: Result offset.

    Returns:
        None.
    """
    run_client(ctx, SkillsListCommand(limit=limit, offset=offset), handle_skills_list)


@skills_app.command("search")
def skills_search(
    ctx: typer.Context,
    query: str,
    tool: list[str] | None = typer.Option(None, "--tool"),
    risk_level: SkillRiskLevel | None = typer.Option(None, "--risk-level"),
    tag: list[str] | None = typer.Option(None, "--tag"),
    limit: int = typer.Option(20, "--limit"),
    offset: int = typer.Option(0, "--offset"),
) -> None:
    """Search skill candidates without full content.

    Args:
        ctx: Typer context.
        query: Search query.
        tool: Repeatable required tool filter.
        risk_level: Optional skill risk filter.
        tag: Repeatable tag filter.
        limit: Maximum result count.
        offset: Result offset.

    Returns:
        None.
    """
    run_client(
        ctx,
        SkillsSearchCommand(
            query=query,
            tool=values(tool),
            risk_level=risk_level,
            tag=values(tag),
            limit=limit,
            offset=offset,
        ),
        handle_skills_search,
    )


@skills_app.command("get")
def skills_get(ctx: typer.Context, item_id: str) -> None:
    """Read one skill.

    Args:
        ctx: Typer context.
        item_id: Skill identifier.

    Returns:
        None.
    """
    run_client(ctx, ItemIdCommand(item_id=item_id), handle_skills_get)


@skills_app.command("create")
def skills_create(
    ctx: typer.Context,
    title: str = typer.Option(..., "--title"),
    purpose: str = typer.Option(..., "--purpose"),
    content: str | None = typer.Option(None, "--content"),
    content_file: str | None = typer.Option(None, "--content-file"),
    summary: str | None = typer.Option(None, "--summary"),
    category_id: str | None = typer.Option(None, "--category-id"),
    tag: list[str] | None = typer.Option(None, "--tag"),
    tool: list[str] | None = typer.Option(None, "--tool"),
    usage_example: str | None = typer.Option(None, "--usage-example"),
    risk_level: SkillRiskLevel = typer.Option(SkillRiskLevel.LOW, "--risk-level"),
    version: str = typer.Option("1.0.0", "--version"),
    created_by: str = typer.Option("Hermes CLI", "--created-by"),
    active: bool = typer.Option(False, "--active"),
    source_agent: str | None = typer.Option(None, "--source-agent"),
    evidence_url: list[str] | None = typer.Option(None, "--evidence-url"),
    source_summary: str | None = typer.Option(None, "--source-summary"),
) -> None:
    """Create a manual skill or submit an agent-authored candidate.

    Args:
        ctx: Typer context.
        title: Skill title.
        purpose: Skill purpose.
        content: Inline skill content.
        content_file: File containing skill content.
        summary: Optional skill summary.
        category_id: Optional category identifier.
        tag: Repeatable tags.
        tool: Repeatable related tools.
        usage_example: Optional usage example.
        risk_level: Skill risk level.
        version: Skill version.
        created_by: Creator display name.
        active: Whether the skill is active.
        source_agent: Agent name for self-acquired candidate submissions.
        evidence_url: Repeatable source URLs for self-acquired candidates.
        source_summary: Optional source/evidence summary.

    Returns:
        None.
    """
    run_client(
        ctx,
        SkillsCreateCommand(
            title=title,
            purpose=purpose,
            content=content,
            content_file=content_file,
            summary=summary,
            category_id=category_id,
            tag=values(tag),
            tool=values(tool),
            usage_example=usage_example,
            risk_level=risk_level,
            version=version,
            created_by=created_by,
            active=active,
            source_agent=source_agent,
            evidence_url=values(evidence_url),
            source_summary=source_summary,
        ),
        handle_skills_create,
    )


@skills_app.command("delete")
def skills_delete(ctx: typer.Context, item_id: str) -> None:
    """Delete a skill.

    Args:
        ctx: Typer context.
        item_id: Skill identifier.

    Returns:
        None.
    """
    run_client(ctx, ItemIdCommand(item_id=item_id), handle_skills_delete)


@folders_app.command("list")
def folders_list(
    ctx: typer.Context,
    tree: bool = typer.Option(False, "--tree", help="Show nested tree"),
) -> None:
    """List folders.

    Args:
        ctx: Typer context.
        tree: Whether to render a nested tree.

    Returns:
        None.
    """
    run_client(ctx, FoldersListCommand(tree=tree), handle_folders_list)


@folders_app.command("create")
def folders_create(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name"),
    parent_id: str | None = typer.Option(None, "--parent-id"),
) -> None:
    """Create a folder.

    Args:
        ctx: Typer context.
        name: Folder name.
        parent_id: Optional parent folder identifier.

    Returns:
        None.
    """
    run_client(
        ctx,
        FoldersCreateCommand(name=name, parent_id=parent_id),
        handle_folders_create,
    )


@folders_app.command("ensure")
def folders_ensure(
    ctx: typer.Context,
    path: str = typer.Option(..., "--path"),
) -> None:
    """Ensure a slash-separated folder path exists.

    Args:
        ctx: Typer context.
        path: Slash-separated folder path.

    Returns:
        None.
    """
    run_client(ctx, FoldersEnsureCommand(path=path), handle_folders_ensure)


@folders_app.command("mkdir")
def folders_mkdir(ctx: typer.Context, path: str) -> None:
    """Alias for ensuring a slash-separated folder path exists.

    Args:
        ctx: Typer context.
        path: Slash-separated folder path.

    Returns:
        None.
    """
    run_client(ctx, FoldersEnsureCommand(path=path), handle_folders_ensure)


@folders_app.command("delete")
def folders_delete(ctx: typer.Context, folder_id: str) -> None:
    """Delete a folder.

    Args:
        ctx: Typer context.
        folder_id: Folder identifier.

    Returns:
        None.
    """
    run_client(ctx, FolderIdCommand(folder_id=folder_id), handle_folders_delete)


@library_app.command("list")
def library_list(
    ctx: typer.Context,
    limit: int = typer.Option(20, "--limit"),
    offset: int = typer.Option(0, "--offset"),
    item_type: LibraryItemType | None = typer.Option(None, "--type"),
    folder_id: str | None = typer.Option(None, "--folder-id"),
    query: str | None = typer.Option(None, "--query"),
) -> None:
    """List all library items.

    Args:
        ctx: Typer context.
        limit: Maximum number of items.
        offset: Result offset.
        item_type: Optional item type filter.
        folder_id: Optional folder identifier.
        query: Optional search query.

    Returns:
        None.
    """
    run_client(
        ctx,
        LibraryListCommand(
            limit=limit,
            offset=offset,
            item_type=item_type,
            folder_id=folder_id,
            query=query,
        ),
        handle_library_list,
    )


@library_app.command("search")
def library_search(
    ctx: typer.Context,
    query: str,
    item_type: LibraryItemType | None = typer.Option(None, "--type"),
    limit: int = typer.Option(20, "--limit"),
    offset: int = typer.Option(0, "--offset"),
    content_mode: str = typer.Option("candidate", "--content-mode"),
) -> None:
    """Search library items.

    Args:
        ctx: Typer context.
        query: Search query.
        item_type: Optional item type filter.
        limit: Maximum result count.
        offset: Result offset.
        content_mode: Candidate content mode.

    Returns:
        None.
    """
    run_client(
        ctx,
        LibrarySearchCommand(
            query=query,
            item_type=item_type,
            limit=limit,
            offset=offset,
            content_mode=content_mode,
        ),
        handle_library_search,
    )


@minio_app.command("scan")
def minio_scan(
    ctx: typer.Context,
    limit: int = typer.Option(24, "--limit"),
    item_type: LibraryItemType | None = typer.Option(None, "--type"),
) -> None:
    """Preview import candidates.

    Args:
        ctx: Typer context.
        limit: Maximum number of candidates.
        item_type: Optional item type filter.

    Returns:
        None.
    """
    run_client(
        ctx,
        MinioCommand(limit=limit, item_type=item_type),
        handle_minio_scan,
    )


@minio_app.command("import")
def minio_import(
    ctx: typer.Context,
    limit: int = typer.Option(48, "--limit"),
    item_type: LibraryItemType | None = typer.Option(None, "--type"),
) -> None:
    """Import linked candidates.

    Args:
        ctx: Typer context.
        limit: Maximum number of candidates.
        item_type: Optional item type filter.

    Returns:
        None.
    """
    run_client(
        ctx,
        MinioCommand(limit=limit, item_type=item_type),
        handle_minio_import,
    )
