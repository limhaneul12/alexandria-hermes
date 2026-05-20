"""Human-readable and JSON output helpers for CLI commands."""

from __future__ import annotations

from typing import TextIO

from app.cli_support.contracts.runtime_contracts import CommandContext
from app.shared.serialization.orjson_codec import dumps_json, dumps_pretty_json
from app.shared.types.extra_types import JSONObject, JSONValue


def print_json(payload: JSONValue, stdout: TextIO) -> None:
    """Print pretty JSON to the selected stream.

    Args:
        payload: JSON-compatible payload.
        stdout: Destination stream.

    Returns:
        None.
    """
    print(dumps_pretty_json(payload).decode("utf-8"), file=stdout)


def print_context_payload(payload: JSONValue, context: CommandContext) -> None:
    """Print context command output.

    Args:
        payload: Backend response payload.
        context: CLI runtime context with output preferences.
    """
    if context.json_output:
        print_json(payload, context.stdout)
        return
    if isinstance(payload, dict):
        if "context_pack" in payload:
            context_pack = payload.get("context_pack")
            rendered_pack = "" if context_pack is None else str(context_pack)
            print(rendered_pack, file=context.stdout)
            return
        title = text_field(payload, "title")
        item_id = text_field(payload, "id")
        status = text_field(payload, "status")
        summary = " ".join(part for part in (status, item_id, title) if part)
        serialized_payload = dumps_json(payload).decode("utf-8")
        rendered_summary = serialized_payload if summary == "" else summary
        print(rendered_summary, file=context.stdout)
        return
    print_json(payload, context.stdout)


def print_hermes_payload(payload: JSONValue, context: CommandContext) -> None:
    """Print Hermes integration command output.

    Args:
        payload: Backend or local integration payload.
        context: CLI runtime context with output preferences.
    """
    print_written_skipped_payload(payload, context, "Hermes integration")


def print_codex_payload(payload: JSONValue, context: CommandContext) -> None:
    """Print Codex integration command output.

    Args:
        payload: Local Codex integration payload.
        context: CLI runtime context with output preferences.
    """
    print_written_skipped_payload(payload, context, "Codex integration")


def print_written_skipped_payload(
    payload: JSONValue,
    context: CommandContext,
    label: str,
) -> None:
    """Print local integration output with written/skipped counts.

    Args:
        payload: Local integration payload.
        context: CLI runtime context with output preferences.
        label: Human-readable integration label.

    Returns:
        None.
    """
    if context.json_output:
        print_json(payload, context.stdout)
        return
    if isinstance(payload, dict):
        written = list_field(payload, "written")
        skipped = list_field(payload, "skipped")
        print(
            f"{label}: {len(written)} written, {len(skipped)} skipped",
            file=context.stdout,
        )
        return
    print_json(payload, context.stdout)


def print_json_or_summary(
    payload: JSONValue,
    context: CommandContext,
    label: str,
) -> None:
    """Print JSON output or a compact summary line.

    Args:
        payload: Backend response payload.
        context: CLI runtime context.
        label: Human-readable result label.

    Returns:
        None.
    """
    if context.json_output:
        print_json(payload, context.stdout)
        return
    if isinstance(payload, list):
        print(f"{label}: {len(payload)}", file=context.stdout)
        return
    item_id = text_field(payload, "id")
    suffix = f" {item_id}" if item_id else ""
    print(f"{label}{suffix}", file=context.stdout)


def print_item_table(
    payload: JSONValue,
    stdout: TextIO,
    empty_message: str = "No skills found.",
) -> None:
    """Print library item rows.

    Args:
        payload: Backend list response payload.
        stdout: Destination stream.
        empty_message: Message printed when no rows are present.
    """
    rows = json_list(payload)
    if len(rows) == 0:
        print(empty_message, file=stdout)
        return
    print("ID\tTYPE\tTITLE", file=stdout)
    for item in rows:
        item_id = text_field(item, "id")
        item_type = text_field(item, "item_type")
        title = text_field(item, "title")
        print(f"{item_id}\t{item_type}\t{title}", file=stdout)


def print_prompt_table(
    payload: JSONValue,
    stdout: TextIO,
    empty_message: str = "No prompts found.",
) -> None:
    """Print prompt item rows.

    Args:
        payload: Backend list response payload.
        stdout: Destination stream.
        empty_message: Message printed when no rows are present.
    """
    rows = json_list(payload)
    if len(rows) == 0:
        print(empty_message, file=stdout)
        return
    print("ID\tTYPE\tKIND\tTITLE", file=stdout)
    for item in rows:
        item_id = text_field(item, "id")
        item_type = text_field(item, "item_type")
        kind = detail_text(item, "prompt_kind")
        title = text_field(item, "title")
        print(f"{item_id}\t{item_type}\t{kind}\t{title}", file=stdout)


def detail_text(payload: JSONValue, key: str) -> str:
    """Read a string field from a nested details payload.

    Args:
        payload: Backend response payload.
        key: Details field name to read.

    Returns:
        String value, or an empty string when absent.
    """
    if not isinstance(payload, dict):
        return ""
    details = payload.get("details")
    if not isinstance(details, dict):
        return ""
    value = details.get(key)
    if isinstance(value, str):
        return value
    return ""


def list_field(payload: JSONValue, key: str) -> list[str]:
    """Read a string list field from a dynamic response payload.

    Args:
        payload: Backend response payload.
        key: Field name to read.

    Returns:
        List of string values, or an empty list when absent.
    """
    if not isinstance(payload, dict):
        return []
    value = payload.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def print_folder_table(payload: JSONValue, stdout: TextIO, tree: bool) -> None:
    """Print folder rows or a tree view.

    Args:
        payload: Backend folder response payload.
        stdout: Destination stream.
        tree: Whether rows should be rendered hierarchically.
    """
    rows = json_list(payload)
    if len(rows) == 0:
        print("No folders found.", file=stdout)
        return
    print("ID\tPARENT\tNAME", file=stdout)
    if tree:
        for item in rows:
            print_folder_tree_row(item, stdout, depth=0)
    else:
        for item in rows:
            folder_id = text_field(item, "id")
            parent_id = display_parent_id(item)
            name = text_field(item, "name")
            print(f"{folder_id}\t{parent_id}\t{name}", file=stdout)


def print_folder_tree_row(item: JSONObject, stdout: TextIO, depth: int) -> None:
    """Print one folder tree row and its children.

    Args:
        item: Folder JSON object from the backend.
        stdout: Destination stream.
        depth: Tree depth used for indentation.
    """
    folder_id = text_field(item, "id")
    parent_id = display_parent_id(item)
    name = text_field(item, "name")
    indent = "  " * depth
    print(f"{folder_id}\t{parent_id}\t{indent}{name}", file=stdout)
    children = item.get("children")
    if not isinstance(children, list):
        return
    for child in children:
        if isinstance(child, dict):
            print_folder_tree_row(child, stdout, depth + 1)


def json_list(payload: JSONValue) -> list[JSONObject]:
    """Normalize a dynamic payload into JSON object rows.

    Args:
        payload: Backend response payload.

    Returns:
        List of JSON objects contained in the payload.
    """
    if isinstance(payload, dict):
        items = payload.get("items")
        if not isinstance(items, list):
            return []
        return [item for item in items if isinstance(item, dict)]
    if not isinstance(payload, list):
        return []
    rows = [item for item in payload if isinstance(item, dict)]
    return rows


def text_field(payload: JSONValue, key: str) -> str:
    """Read a scalar field as display text.

    Args:
        payload: Backend response payload.
        key: Field name to render.

    Returns:
        Display string, or an empty string when absent.
    """
    if not isinstance(payload, dict):
        return ""
    value = payload.get(key)
    if isinstance(value, str):
        return value
    if isinstance(value, int | float | bool):
        return str(value)
    return ""


def display_parent_id(payload: JSONValue) -> str:
    """Render an optional folder parent id.

    Args:
        payload: Backend folder payload.

    Returns:
        Parent id or '-' when the folder has no parent.
    """
    parent_id = text_field(payload, "parent_id")
    rendered_parent = "-" if parent_id == "" else parent_id
    return rendered_parent
