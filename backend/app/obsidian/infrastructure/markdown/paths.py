"""Filesystem path helpers for Obsidian vault access."""

from __future__ import annotations

import re
from pathlib import Path

from app.shared.exceptions import ObsidianValidationError

NOTE_SUFFIX = ".md"
_SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9가-힣._ -]+")


def resolve_vault_path(vault_path: str | Path) -> Path:
    """Resolve an Obsidian vault root path.

    Args:
        vault_path: User or config supplied vault root.

    Returns:
        Absolute path for the vault root.
    """
    vault = Path(vault_path).expanduser()
    if not vault.is_absolute():
        vault = Path.cwd() / vault
    return vault.resolve()


def safe_relative_path(relative_path: str | Path) -> Path:
    """Validate a vault-relative path.

    Args:
        relative_path: Path supplied by an API/client.

    Returns:
        Safe relative Path.
    """
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ObsidianValidationError("Obsidian path must stay inside the vault")
    return relative


def resolve_note_path(vault_path: str | Path, relative_path: str | Path) -> Path:
    """Resolve one safe note path inside a vault.

    Args:
        vault_path: Vault root path.
        relative_path: Vault-relative note path.

    Returns:
        Absolute note path.
    """
    vault = resolve_vault_path(vault_path)
    relative = safe_relative_path(relative_path)
    target = (vault / relative).resolve()
    if vault not in target.parents and target != vault:
        raise ObsidianValidationError("Obsidian path escaped the vault")
    return target


def safe_filename(title: str) -> str:
    """Return a filesystem-friendly Markdown filename for a note title.

    Args:
        title: Human title.

    Returns:
        Safe filename ending with `.md`.
    """
    cleaned = _SAFE_FILENAME_PATTERN.sub("", title).strip(" .")
    filename = cleaned or "Untitled"
    if not filename.endswith(NOTE_SUFFIX):
        filename = f"{filename}{NOTE_SUFFIX}"
    return filename
