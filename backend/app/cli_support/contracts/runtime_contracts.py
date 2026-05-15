"""Shared contracts for the Alexandria-Hermes CLI."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_TIMEOUT_SECONDS = 30.0
HERMES_CONFIG_ENV = "ALEXANDRIA_HERMES_CONFIG"

HttpHeaders = dict[str, str]
HttpResponse = tuple[int, bytes]
HttpTransport = Callable[[str, str, bytes | None, HttpHeaders, float], HttpResponse]


@dataclass(frozen=True, slots=True)
class CommandContext:
    """Runtime dependencies and presentation options for one CLI invocation."""

    base_url: str
    json_output: bool
    timeout: float
    stdout: TextIO
    stderr: TextIO
    transport: HttpTransport


@dataclass(frozen=True, slots=True)
class CliRuntime:
    """Injected process resources for one Typer CLI invocation."""

    transport: HttpTransport
    stdout: TextIO
    stderr: TextIO


@dataclass(frozen=True, slots=True)
class HermesInstallFile:
    """One file planned for Hermes integration installation."""

    relative_path: str
    content: str


@dataclass(frozen=True, slots=True)
class HermesResolvedHome:
    """Resolved Hermes home directory and its source."""

    path: Path
    source: str
