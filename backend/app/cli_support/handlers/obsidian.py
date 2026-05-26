"""Handlers for Obsidian CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import cast
from urllib.parse import quote

from app.cli_support.backend_api_client import CliBackendApiClient
from app.cli_support.contracts.obsidian_command_contracts import (
    ObsidianAskCommand,
    ObsidianCaptureCommand,
    ObsidianReadCommand,
    ObsidianRelatedCommand,
    ObsidianSaveCommand,
    ObsidianSearchCommand,
)
from app.cli_support.contracts.runtime_contracts import CommandContext
from app.cli_support.presentation.output_renderers import print_json
from app.obsidian.domain.event_enum.obsidian_enums import AlexandriaNoteType
from app.shared.exceptions.cli_exceptions import CliInputError
from app.shared.serialization.orjson_codec import loads_json
from app.shared.types.extra_types import JSONObject, JSONValue

_CAPTURE_TYPES = frozenset(
    {
        AlexandriaNoteType.MEMORY_COMPACT,
        AlexandriaNoteType.SKILL,
        AlexandriaNoteType.PROMPT,
    }
)
_CAPTURE_DEFAULT_TAGS: dict[AlexandriaNoteType, tuple[str, ...]] = {
    AlexandriaNoteType.MEMORY_COMPACT: ("alexandria", "memory-compact"),
    AlexandriaNoteType.SKILL: ("alexandria", "skill", "draft"),
    AlexandriaNoteType.PROMPT: ("alexandria", "prompt", "template"),
}


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
    response = client.post("/obsidian/notes", _save_payload(command))
    _emit(context, response)
    return 0


def handle_obsidian_capture(
    command: ObsidianCaptureCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Capture one canonical memory/skill/prompt artifact into Obsidian.

    Args:
        command: Capture command parameters.
        context: CLI command context.
        client: Backend API client.

    Returns:
        Process exit code.
    """
    if command.alexandria_type not in _CAPTURE_TYPES:
        allowed = ", ".join(sorted(note_type.value for note_type in _CAPTURE_TYPES))
        raise CliInputError(f"capture --type must be one of: {allowed}")
    response = client.post("/obsidian/notes", _capture_payload(command))
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


def _save_payload(command: ObsidianSaveCommand) -> JSONObject:
    body_path = Path(command.body_file).expanduser()
    payload: JSONObject = {
        "title": command.title,
        "body": body_path.read_text(encoding="utf-8"),
        "alexandria_type": command.alexandria_type.value,
        "tags": command.tags,
        "status": command.status,
        "source": command.source,
        "frontmatter": _frontmatter(command.frontmatter_json),
    }
    _add_optional_note_fields(
        payload,
        note_id=command.note_id,
        path=command.path,
        project=command.project,
    )
    return payload


def _capture_payload(command: ObsidianCaptureCommand) -> JSONObject:
    body_path = Path(command.body_file).expanduser()
    frontmatter = _capture_frontmatter(command)
    payload: JSONObject = {
        "title": command.title,
        "body": body_path.read_text(encoding="utf-8"),
        "alexandria_type": command.alexandria_type.value,
        "tags": _capture_tags(command.alexandria_type, command.tags),
        "status": command.status,
        "source": command.source,
        "frontmatter": frontmatter,
    }
    _add_optional_note_fields(
        payload,
        note_id=command.note_id,
        path=command.path,
        project=command.project,
    )
    return payload


def _add_optional_note_fields(
    payload: JSONObject,
    *,
    note_id: str | None,
    path: str | None,
    project: str | None,
) -> None:
    if note_id is not None:
        payload["id"] = note_id
    if path is not None:
        payload["path"] = path
    if project is not None:
        payload["project"] = project


def _capture_frontmatter(command: ObsidianCaptureCommand) -> JSONObject:
    frontmatter = _frontmatter(command.frontmatter_json)
    frontmatter.setdefault("artifact_kind", command.alexandria_type.value)
    if command.alexandria_type is AlexandriaNoteType.MEMORY_COMPACT:
        if command.covered_from is not None:
            frontmatter["covered_from"] = command.covered_from
        if command.covered_to is not None:
            frontmatter["covered_to"] = command.covered_to
    elif command.alexandria_type is AlexandriaNoteType.SKILL:
        frontmatter.setdefault("skill_status", "draft")
        frontmatter.setdefault("review_status", "needs_review")
    elif command.alexandria_type is AlexandriaNoteType.PROMPT:
        frontmatter.setdefault("prompt_kind", command.prompt_kind or "template")
    return frontmatter


def _frontmatter(raw_json: str | None) -> JSONObject:
    if raw_json is None:
        return {}
    try:
        decoded = loads_json(raw_json)
    except ValueError as exc:
        raise CliInputError("--frontmatter-json must be valid JSON") from exc
    if not isinstance(decoded, dict):
        raise CliInputError("--frontmatter-json must be a JSON object")
    return cast(JSONObject, dict(decoded))


def _capture_tags(
    note_type: AlexandriaNoteType,
    tags: list[str],
) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for tag in [*_CAPTURE_DEFAULT_TAGS[note_type], *tags]:
        normalized = tag.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(normalized)
    return merged
