"""Usage concept enum definitions."""

from __future__ import annotations

from enum import StrEnum


class SelectionSource(StrEnum):
    """How an item was chosen by an agent."""

    RECOMMENDATION = "RECOMMENDATION"
    MANUAL_BROWSE = "MANUAL_BROWSE"
    SEARCH = "SEARCH"
    DIRECT_LINK = "DIRECT_LINK"
