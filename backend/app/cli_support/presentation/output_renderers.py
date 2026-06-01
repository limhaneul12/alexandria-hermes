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
