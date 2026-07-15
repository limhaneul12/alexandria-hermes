"""Typer app assembly for librarian and second-brain bridge commands."""

from __future__ import annotations

import typer

from app.cli.librarian_readiness_commands import register_librarian_readiness_commands
from app.cli.librarian_review_commands import register_librarian_review_commands

librarian_app = typer.Typer(
    help="Operate Alexandria librarian workflows.",
    no_args_is_help=True,
    add_completion=False,
)
register_librarian_readiness_commands(librarian_app)
register_librarian_review_commands(librarian_app)
