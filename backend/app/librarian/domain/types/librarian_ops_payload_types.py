"""Typed payload contracts for librarian operation helpers."""

from __future__ import annotations

from app.library.domain.event_enum.item_enums import ItemType
from typing_extensions import TypedDict


class LibrarianClassificationPayload(TypedDict, closed=True):
    """Public payload for text classification results."""

    label: ItemType
    confidence: float
