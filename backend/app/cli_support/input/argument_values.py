"""Scalar value normalization helpers for CLI inputs."""

from __future__ import annotations


def bounded_limit(value: int, default: int) -> int:
    """Clamp a CLI limit to the backend-safe range.

    Args:
        value: Requested limit.
        default: Default limit for non-positive requests.

    Returns:
        Limit between 1 and 1000.
    """
    candidate = int(value) if value > 0 else default
    bounded = min(max(candidate, 1), 1000)
    return bounded


def optional_text(value: str | None) -> str | None:
    """Normalize optional text arguments.

    Args:
        value: Raw optional text.

    Returns:
        Stripped text, or None when blank.
    """
    if value is None:
        return None
    stripped = value.strip()
    normalized = None if stripped == "" else stripped
    return normalized
