"""Public CLI entrypoint for Alexandria-Hermes."""

from __future__ import annotations

from app.cli_support.contracts.runtime_contracts import (
    HttpHeaders,
    HttpResponse,
    HttpTransport,
)
from app.cli_support.core.runtime import main, run
from app.cli_support.typer_entry import typer_app

__all__ = [
    "HttpHeaders",
    "HttpResponse",
    "HttpTransport",
    "main",
    "run",
    "typer_app",
]


if __name__ == "__main__":
    raise SystemExit(main())
