"""Common helpers for native Typer command modules."""

from __future__ import annotations

from collections.abc import Callable

import typer
from app.cli_support.contracts.runtime_contracts import (
    CommandContext,
)
from app.cli_support.transport.backend_api_client import CliBackendApiClient
from app.shared.exceptions.cli_exceptions import (
    CliInputError,
    CliRequestError,
    CliRuntimeStateError,
)

type ClientHandler[CommandT] = Callable[
    [CommandT, CommandContext, CliBackendApiClient],
    int,
]
type LocalHandler[CommandT] = Callable[[CommandT, CommandContext], int]
type StandaloneHandler[CommandT] = Callable[[CommandT], int]
type ContextHandler = Callable[[CommandContext, CliBackendApiClient], int]


def command_context(ctx: typer.Context) -> CommandContext:
    """Return the root CLI command context.

    Args:
        ctx: Typer context from a command callback.

    Returns:
        CLI command context stored by the root callback.
    """
    root_obj = ctx.find_root().obj
    if not isinstance(root_obj, CommandContext):
        raise CliRuntimeStateError("CLI context was not initialized")
    return root_obj


def run_client[CommandT](
    ctx: typer.Context,
    command: CommandT,
    handler: ClientHandler[CommandT],
) -> None:
    """Run a handler that needs command data, context, and HTTP client.

    Args:
        ctx: Typer context from a command callback.
        command: Typed command parameters.
        handler: Handler function to execute.

    Returns:
        None.
    """
    context = command_context(ctx)
    client = CliBackendApiClient(context)
    _exit_with_result(lambda: handler(command, context, client), context)


def run_local[CommandT](
    ctx: typer.Context,
    command: CommandT,
    handler: LocalHandler[CommandT],
) -> None:
    """Run a handler that needs command data and context only.

    Args:
        ctx: Typer context from a command callback.
        command: Typed command parameters.
        handler: Handler function to execute.

    Returns:
        None.
    """
    context = command_context(ctx)
    _exit_with_result(lambda: handler(command, context), context)


def run_standalone[CommandT](
    command: CommandT,
    handler: StandaloneHandler[CommandT],
) -> None:
    """Run a handler that owns its own process boundary.

    Args:
        command: Typed command parameters.
        handler: Handler function to execute.

    Returns:
        None.
    """
    try:
        exit_code = handler(command)
    except (CliInputError, CliRequestError, OSError) as exc:
        raise typer.Exit(1) from exc
    raise typer.Exit(exit_code)


def run_context(ctx: typer.Context, handler: ContextHandler) -> None:
    """Run a handler that only needs context and HTTP client.

    Args:
        ctx: Typer context from a command callback.
        handler: Handler function to execute.

    Returns:
        None.
    """
    context = command_context(ctx)
    client = CliBackendApiClient(context)
    _exit_with_result(lambda: handler(context, client), context)


def values(raw: list[str] | None) -> list[str]:
    """Normalize repeatable Typer option values.

    Args:
        raw: Optional list emitted by Typer.

    Returns:
        A concrete list for handler compatibility.
    """
    if raw is None:
        normalized: list[str] = []
    else:
        normalized = raw
    return normalized


def _exit_with_result(action: Callable[[], int], context: CommandContext) -> None:
    try:
        exit_code = action()
    except (CliInputError, CliRequestError, OSError) as exc:
        print(f"error: {exc}", file=context.stderr)
        raise typer.Exit(1) from exc
    raise typer.Exit(exit_code)
