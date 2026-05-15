"""Handlers for library, skill, folder, and MINIO CLI commands."""

from __future__ import annotations

import urllib.parse

from app.cli_support.contracts.command_contracts import (
    FolderIdCommand,
    FoldersCreateCommand,
    FoldersListCommand,
    ItemIdCommand,
    LibraryListCommand,
    LibrarySearchCommand,
    MinioCommand,
    SkillsCreateCommand,
    SkillsListCommand,
)
from app.cli_support.contracts.request_mappers import (
    folder_create_payload,
    minio_import_payload,
    skill_create_payload,
)
from app.cli_support.contracts.runtime_contracts import CommandContext
from app.cli_support.input.argument_values import bounded_limit
from app.cli_support.presentation.output_renderers import (
    json_list,
    print_candidate_table,
    print_folder_table,
    print_item_table,
    print_json,
    text_field,
)
from app.cli_support.routing.url_paths import quote_path
from app.cli_support.schemas.library_command_schemas import DeletedResourceResult
from app.cli_support.serialization.json_payloads import schema_payload
from app.cli_support.transport.backend_api_client import CliBackendApiClient


def handle_health(context: CommandContext, client: CliBackendApiClient) -> int:
    """Run the health CLI command.

    Args:
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    payload = client.get("/health/live")
    if context.json_output:
        print_json(payload, context.stdout)
    else:
        print("Hermes backend is reachable", file=context.stdout)
    return 0


def handle_skills_list(
    command: SkillsListCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the skills list CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    limit = bounded_limit(command.limit, default=20)
    offset = max(0, int(command.offset))
    payload = client.get(f"/skills?limit={limit}&offset={offset}")
    if context.json_output:
        print_json(payload, context.stdout)
    else:
        print_item_table(payload, context.stdout)
    return 0


def handle_skills_get(
    command: ItemIdCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the skills get CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    item_id = str(command.item_id)
    payload = client.get(f"/skills/{quote_path(item_id)}")
    print_json(payload, context.stdout)
    return 0


def handle_skills_create(
    command: SkillsCreateCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the skills create CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    body = skill_create_payload(command)
    payload = client.post("/skills", body)
    if context.json_output:
        print_json(payload, context.stdout)
    else:
        title = text_field(payload, "title")
        item_id = text_field(payload, "id")
        print(f"created skill {item_id}: {title}", file=context.stdout)
    return 0


def handle_skills_delete(
    command: ItemIdCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the skills delete CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    item_id = str(command.item_id)
    client.delete(f"/skills/{quote_path(item_id)}")
    if context.json_output:
        result = DeletedResourceResult(deleted=item_id)
        print_json(schema_payload(result), context.stdout)
    else:
        print(f"deleted skill {item_id}", file=context.stdout)
    return 0


def handle_folders_list(
    command: FoldersListCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the folders list CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    path = "/categories/tree" if bool(command.tree) else "/categories"
    payload = client.get(path)
    if context.json_output:
        print_json(payload, context.stdout)
    else:
        print_folder_table(payload, context.stdout, tree=bool(command.tree))
    return 0


def handle_folders_create(
    command: FoldersCreateCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the folders create CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    body = folder_create_payload(command)
    payload = client.post("/categories", body)
    if context.json_output:
        print_json(payload, context.stdout)
    else:
        folder_id = text_field(payload, "id")
        name = text_field(payload, "name")
        print(f"created folder {folder_id}: {name}", file=context.stdout)
    return 0


def handle_folders_delete(
    command: FolderIdCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the folders delete CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    folder_id = str(command.folder_id)
    client.delete(f"/categories/{quote_path(folder_id)}")
    if context.json_output:
        result = DeletedResourceResult(deleted=folder_id)
        print_json(schema_payload(result), context.stdout)
    else:
        print(f"deleted folder {folder_id}", file=context.stdout)
    return 0


def handle_library_list(
    command: LibraryListCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the library list CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    params = [
        ("limit", str(bounded_limit(command.limit, default=20))),
        ("offset", str(max(0, int(command.offset)))),
    ]
    if command.item_type is not None:
        params.append(("item_type", command.item_type.value))
    if command.folder_id is not None:
        params.append(("category_id", command.folder_id))
    if command.query is not None:
        params.append(("q", command.query))
    query = urllib.parse.urlencode(params)
    payload = client.get(f"/items?{query}")
    if context.json_output:
        print_json(payload, context.stdout)
    else:
        print_item_table(
            payload, context.stdout, empty_message="No library items found."
        )
    return 0


def handle_library_search(
    command: LibrarySearchCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the library search CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    query = urllib.parse.urlencode({"q": str(command.query)})
    payload = client.get(f"/search?{query}")
    if context.json_output:
        print_json(payload, context.stdout)
    else:
        print_item_table(
            payload, context.stdout, empty_message="No matching items found."
        )
    return 0


def handle_minio_scan(
    command: MinioCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the minio scan CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    limit = bounded_limit(command.limit, default=24)
    payload = client.get(f"/storage/minio/import-candidates?limit={limit}")
    if command.item_type is not None:
        rows = [
            row
            for row in json_list(payload)
            if text_field(row, "item_type") == command.item_type.value
        ]
        payload = rows
    if context.json_output:
        print_json(payload, context.stdout)
    else:
        print_candidate_table(payload, context.stdout)
    return 0


def handle_minio_import(
    command: MinioCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the minio import CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    limit = bounded_limit(command.limit, default=48)
    payload = client.post(
        "/storage/minio/import",
        minio_import_payload(MinioCommand(limit=limit, item_type=command.item_type)),
    )
    if context.json_output:
        print_json(payload, context.stdout)
    else:
        imported = text_field(payload, "imported_count")
        skipped = text_field(payload, "skipped_count")
        print(
            f"MINIO sync complete: {imported} imported, {skipped} skipped",
            file=context.stdout,
        )
    return 0
