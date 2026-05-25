"""Handlers for Obsidian CLI commands."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from app.cli_support.backend_api_client import CliBackendApiClient
from app.cli_support.contracts.obsidian_command_contracts import (
    ObsidianAskCommand,
    ObsidianReadCommand,
    ObsidianRelatedCommand,
    ObsidianSaveCommand,
    ObsidianSearchCommand,
)
from app.cli_support.contracts.runtime_contracts import CommandContext
from app.cli_support.presentation.output_renderers import print_json
from app.shared.exceptions.cli_exceptions import CliInputError
from app.shared.types.extra_types import JSONObject, JSONValue


def handle_obsidian_status(
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Print Obsidian status.

    Args:
        context: CLI command context.
        client: Backend API client.

    Returns:
        Process exit code.
    """
    payload = client.get("/obsidian/status")
    _emit(context, payload)
    return 0


def handle_obsidian_init(
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Initialize Obsidian vault layout.

    Args:
        context: CLI command context.
        client: Backend API client.

    Returns:
        Process exit code.
    """
    payload = client.post("/obsidian/init", {})
    _emit(context, payload)
    return 0


def handle_obsidian_reindex(
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Reindex Obsidian vault.

    Args:
        context: CLI command context.
        client: Backend API client.

    Returns:
        Process exit code.
    """
    payload = client.post("/obsidian/index/rebuild", {})
    _emit(context, payload)
    return 0


def handle_obsidian_search(
    command: ObsidianSearchCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Search Obsidian notes.

    Args:
        command: Search command parameters.
        context: CLI command context.
        client: Backend API client.

    Returns:
        Process exit code.
    """
    payload: JSONObject = {
        "query": command.query,
        "limit": command.limit,
        "tags": command.tags,
    }
    if command.alexandria_type is not None:
        payload["alexandria_type"] = command.alexandria_type.value
    if command.project is not None:
        payload["project"] = command.project
    response = client.post("/obsidian/search", payload)
    _emit(context, response)
    return 0


def handle_obsidian_read(
    command: ObsidianReadCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Read one Obsidian note.

    Args:
        command: Read command parameters.
        context: CLI command context.
        client: Backend API client.

    Returns:
        Process exit code.
    """
    if command.path is not None:
        payload = client.get(f"/obsidian/notes/by-path?path={quote(command.path)}")
    elif command.note_id is not None:
        payload = client.get(f"/obsidian/notes/{quote(command.note_id, safe='')}")
    else:
        raise CliInputError("provide either note_id or --path")
    _emit(context, payload)
    return 0


def handle_obsidian_related(
    command: ObsidianRelatedCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Read graph-related Obsidian notes.

    Args:
        command: Related lookup parameters.
        context: CLI command context.
        client: Backend API client.

    Returns:
        Process exit code.
    """
    if command.path is not None:
        payload = client.get(
            f"/obsidian/notes/by-path/related?path={quote(command.path)}&limit={command.limit}"
        )
    elif command.note_id is not None:
        payload = client.get(
            f"/obsidian/notes/{quote(command.note_id, safe='')}/related?limit={command.limit}"
        )
    else:
        raise CliInputError("provide either note_id or --path")
    _emit(context, payload)
    return 0


def handle_obsidian_save(
    command: ObsidianSaveCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Save one Obsidian note from a Markdown body file.

    Args:
        command: Save command parameters.
        context: CLI command context.
        client: Backend API client.

    Returns:
        Process exit code.
    """
    body_path = Path(command.body_file).expanduser()
    body = body_path.read_text(encoding="utf-8")
    payload: JSONObject = {
        "title": command.title,
        "body": body,
        "alexandria_type": command.alexandria_type.value,
        "tags": command.tags,
    }
    if command.note_id is not None:
        payload["id"] = command.note_id
    if command.path is not None:
        payload["path"] = command.path
    if command.project is not None:
        payload["project"] = command.project
    response = client.post("/obsidian/notes", payload)
    _emit(context, response)
    return 0


def handle_obsidian_ask(
    command: ObsidianAskCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Ask the Obsidian-aware librarian.

    Args:
        command: Librarian ask command parameters.
        context: CLI command context.
        client: Backend API client.

    Returns:
        Process exit code.
    """
    payload: JSONObject = {
        "query": command.query,
        "save_transcript": command.save_transcript,
    }
    if command.active_note_path is not None:
        payload["active_note_path"] = command.active_note_path
    if command.selection is not None:
        payload["selection"] = command.selection
    if command.project is not None:
        payload["project"] = command.project
    if command.delegate_to_librarian:
        payload["delegate_to_librarian"] = True
    if command.provider_id is not None:
        payload["provider_id"] = command.provider_id
    if command.profile_id is not None:
        payload["profile_id"] = command.profile_id
    response = client.post("/obsidian/librarian/ask", payload)
    _emit(context, response)
    return 0


def _emit(context: CommandContext, payload: JSONValue) -> None:
    if context.json_output:
        print_json(payload, context.stdout)
        return
    print_json(payload, context.stdout)
