"""Runtime entrypoints for the Alexandria-Hermes CLI."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import TextIO

from app.cli_support.backend_api_client import default_transport
from app.cli_support.contracts.runtime_contracts import CliRuntime, HttpTransport
from app.cli_support.typer_entry import invoke_typer_app


def run(
    argv: Sequence[str] | None = None,
    transport: HttpTransport | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run the native Typer CLI command tree.

    Args:
        argv: Optional argument sequence excluding program name.
        transport: Optional HTTP transport override for tests.
        stdout: Optional output stream.
        stderr: Optional error stream.

    Returns:
        Process-style exit code.
    """
    raw_argv = sys.argv[1:] if argv is None else list(argv)
    normalized_argv = normalize_argv(raw_argv)
    output = stdout if stdout is not None else sys.stdout
    errors = stderr if stderr is not None else sys.stderr
    runtime = CliRuntime(
        stdout=output,
        stderr=errors,
        transport=transport if transport is not None else default_transport,
    )
    exit_code = invoke_typer_app(normalized_argv, runtime)
    return exit_code


def normalize_argv(argv: Sequence[str]) -> list[str]:
    """Move global JSON flags before commands for Typer compatibility.

    Args:
        argv: Argument sequence.

    Returns:
        Normalized arguments with --json at the root when present.
    """
    normalized = [arg for arg in argv if arg != "--json"]
    forced_json = len(normalized) != len(argv)
    if forced_json:
        normalized = ["--json", *normalized]
    return normalized


def main(argv: Sequence[str] | None = None) -> int:
    """Console script entrypoint.

    Args:
        argv: Optional argument sequence excluding program name.

    Returns:
        Process-style exit code.
    """
    exit_code = run(argv)
    return exit_code
