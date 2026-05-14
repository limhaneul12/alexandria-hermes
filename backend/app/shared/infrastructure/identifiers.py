"""Identifier helpers for persistent database records."""

from __future__ import annotations

from uuid import uuid4

ID_LENGTH = 36


def new_uuid() -> str:
    """Return a random UUIDv4 string for public database identifiers.

    Returns:
        str: Value produced by new_uuid.
    """
    return str(uuid4())
