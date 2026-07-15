"""CLI JSON output and exit-code helpers."""

from __future__ import annotations

import sys
from collections.abc import Awaitable, Callable

import anyio

from app.mcp_server.backend_api_client import AlexandriaApiError
from app.shared.serialization.orjson_codec import dumps_pretty_json
from app.shared.types.extra_types import JSONValue


def emit_json(payload: JSONValue) -> None:
    """Print a JSON payload to stdout.

    Args:
        payload: JSON-compatible payload to render.
    """
    sys.stdout.buffer.write(dumps_pretty_json(payload))
    sys.stdout.buffer.write(b"\n")


def run_json_command(
    operation: Callable[[], Awaitable[JSONValue]],
    error_prefix: str,
    attention_required: Callable[[JSONValue], bool] | None = None,
) -> int:
    """Run an async CLI operation and map its JSON result to an exit code.

    Args:
        operation: No-argument async operation returning a JSON payload.
        error_prefix: Human-readable stderr prefix for backend/API failures.
        attention_required: Optional predicate that maps a payload to exit code 2.

    Returns:
        Process-style exit code.
    """
    try:
        payload = anyio.run(operation)
    except AlexandriaApiError as exc:
        print(f"{error_prefix}: {exc.message}", file=sys.stderr)
        return 1
    emit_json(payload)
    if attention_required is not None and attention_required(payload):
        return 2
    return 0
