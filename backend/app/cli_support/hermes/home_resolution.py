"""Hermes home path resolution and asset scanning."""

from __future__ import annotations

import os
from pathlib import Path

from app.cli_support.argument_values import optional_text
from app.cli_support.contracts.command_contracts import (
    HermesBundleCommand,
    HermesConfigureCommand,
    HermesDoctorCommand,
    HermesScanCommand,
)
from app.cli_support.contracts.runtime_contracts import (
    HERMES_CONFIG_ENV,
    CommandContext,
    HermesResolvedHome,
)
from app.cli_support.schemas.hermes_integration_schemas import HermesScannedFile
from app.cli_support.url_paths import normalized_base_url
from app.shared.exceptions.cli_exceptions import CliInputError
from app.shared.serialization.orjson_codec import loads_json
from app.shared.utils.config import settings_model_config
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class HermesCliEnvironment(BaseSettings):
    """Typed environment boundary for Hermes CLI path settings."""

    model_config = settings_model_config(env_prefix="")

    hermes_home: str | None = Field(default=None, validation_alias="HERMES_HOME")
    config_path: str | None = Field(
        default=None,
        validation_alias=HERMES_CONFIG_ENV,
    )

    @field_validator("hermes_home", "config_path", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw settings input.
    def empty_to_none(cls, value: object) -> str | None:
        """Normalize blank environment values.

        Args:
            value: Raw environment value.

        Returns:
            Non-empty string or None.
        """
        if not isinstance(value, str):
            return None
        stripped = value.strip()
        return stripped or None


def resolve_hermes_home(
    raw_home: str | None,
    require_source: bool,
) -> HermesResolvedHome:
    """Resolve the Hermes home path from argument, environment, or config.

    Args:
        raw_home: Optional path supplied by CLI argument.
        require_source: Whether missing configured sources should fail.

    Returns:
        Resolved Hermes home path and the source that produced it.

    Raises:
        CliInputError: When no configured home exists and one is required.
    """
    explicit = optional_text(raw_home)
    if explicit is not None:
        resolved = HermesResolvedHome(Path(explicit).expanduser(), "argument")
        return resolved
    env_home = optional_text(HermesCliEnvironment().hermes_home)
    if env_home is not None:
        resolved = HermesResolvedHome(Path(env_home).expanduser(), "HERMES_HOME")
        return resolved
    configured = saved_hermes_home()
    if configured is not None:
        resolved = HermesResolvedHome(configured, "saved_config")
        return resolved
    default_home = Path.home() / ".hermes"
    if default_home.exists() and default_home.is_dir():
        resolved = HermesResolvedHome(default_home, "default")
        return resolved
    if require_source:
        raise CliInputError(
            "HERMES_HOME_REQUIRED: pass --hermes-home or set HERMES_HOME"
        )
    resolved = HermesResolvedHome(default_home, "default")
    return resolved


def saved_hermes_home() -> Path | None:
    """Read the saved Hermes home path from local CLI config.

    Args:
        None.

    Returns:
        Saved path, or None when no valid saved config exists.
    """
    config_path = hermes_config_path()
    if not config_path.exists():
        return None
    try:
        payload = loads_json(config_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    if not isinstance(payload, dict):
        return None
    value = payload.get("hermes_home")
    if not isinstance(value, str) or not value.strip():
        return None
    saved_path = Path(value).expanduser()
    return saved_path


def hermes_config_path() -> Path:
    """Resolve the local Alexandria-Hermes CLI config path.

    Args:
        None.

    Returns:
        Config path from environment or the default user config location.
    """
    configured = optional_text(HermesCliEnvironment().config_path)
    if configured is not None:
        config_path = Path(configured).expanduser()
        return config_path
    config_path = Path.home() / ".config" / "alexandria-hermes" / "config.json"
    return config_path


def validate_hermes_home(path: Path) -> None:
    """Validate a writable Hermes home directory.

    Args:
        path: Candidate Hermes home path.

    Raises:
        CliInputError: When the path is absent, not a directory, or unwritable.
    """
    if not path.exists():
        raise CliInputError(f"Hermes home does not exist: {path}")
    if not path.is_dir():
        raise CliInputError(f"Hermes home is not a directory: {path}")
    if not path_has_write_access(path):
        raise CliInputError(f"Hermes home is not writable: {path}")


def path_has_write_access(path: Path) -> bool:
    """Return whether the current process can write to a path.

    Args:
        path: Filesystem path to check.

    Returns:
        True when the path is writable.
    """
    return os.access(path, os.W_OK)


def hermes_api_url(
    command: HermesBundleCommand | HermesConfigureCommand | HermesDoctorCommand,
    context: CommandContext,
) -> str:
    """Resolve the backend API URL used by Hermes integration commands.

    Args:
        command: CLI command contract with optional API URL.
        context: Runtime context containing the default backend URL.

    Returns:
        Normalized backend API URL.
    """
    raw_url = optional_text(command.api_url)
    if raw_url is not None:
        api_url = normalized_base_url(raw_url)
        return api_url
    api_url = context.base_url
    return api_url


def scan_base_path(command: HermesScanCommand) -> Path:
    """Resolve the directory scanned for Hermes integration files.

    Args:
        command: CLI scan command contract.

    Returns:
        Directory to scan for Alexandria-Hermes assets.
    """
    if command.path is not None:
        base_path = Path(str(command.path)).expanduser()
        return base_path
    resolved = resolve_hermes_home(command.hermes_home, require_source=False)
    base_path = resolved.path / "alexandria-hermes"
    return base_path


def scan_hermes_files(base: Path) -> tuple[HermesScannedFile, ...]:
    """Scan installed Hermes integration files.

    Args:
        base: Directory containing Alexandria-Hermes assets.

    Returns:
        Tuple of discovered Markdown and JSON files with sizes.
    """
    if not base.exists() or not base.is_dir():
        return ()
    rows: list[HermesScannedFile] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.suffix not in {".md", ".json"}:
            continue
        relative_path = str(path.relative_to(base))
        rows.append(
            HermesScannedFile(path=relative_path, size_bytes=path.stat().st_size)
        )
    scanned_files = tuple(rows)
    return scanned_files
