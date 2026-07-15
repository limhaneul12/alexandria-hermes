"""Top-level Typer CLI entrypoint for Alexandria-Hermes."""

from __future__ import annotations

import sys
from collections.abc import Sequence

import click
import typer
from typer.main import get_command

from app.cli.librarian_workflow_commands import librarian_app
from app.cli.mcp_server_commands import mcp_app

app = typer.Typer(
    help="Alexandria-Hermes command line client.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(mcp_app, name="mcp")
app.add_typer(librarian_app, name="librarian")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Alexandria-Hermes command tree.

    Args:
        argv: Optional command arguments without the executable name.

    Returns:
        Process-style exit code.
    """
    try:
        result = get_command(app).main(
            args=list(argv) if argv is not None else None,
            prog_name="alexandria-hermes",
            standalone_mode=False,
        )
        if isinstance(result, int):
            return result
    except typer.Exit as exc:
        return int(exc.exit_code or 0)
    except click.ClickException as exc:
        exc.show(file=sys.stderr)
        return exc.exit_code
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
