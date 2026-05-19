"""URL construction helpers for the Alexandria-Hermes CLI."""

from __future__ import annotations

import urllib.parse

from app.cli_support.contracts.runtime_contracts import DEFAULT_API_URL


def normalized_base_url(value: str) -> str:
    """Normalize a base URL while preserving the project default.

    Args:
        value: Raw URL value.

    Returns:
        URL without a trailing slash, or the default URL when empty.
    """
    normalized = value.rstrip("/")
    result = DEFAULT_API_URL if normalized == "" else normalized
    return result


def join_url(base_url: str, path: str) -> str:
    """Join a normalized base URL with an absolute API path.

    Args:
        base_url: Backend API base URL.
        path: API path beginning with slash.

    Returns:
        Fully qualified request URL.
    """
    joined = f"{base_url}{path}"
    return joined


def quote_path(value: str) -> str:
    """Percent-encode a path segment.

    Args:
        value: Raw path segment.

    Returns:
        Encoded path segment safe for one URL segment.
    """
    quoted = urllib.parse.quote(value, safe="")
    return quoted
