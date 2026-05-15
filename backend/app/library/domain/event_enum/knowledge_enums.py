"""Knowledge concept enum definitions."""

from __future__ import annotations

from enum import StrEnum


class KnowledgeDetailField(StrEnum):
    """Knowledge details keys accepted by public patch payloads."""

    BODY = "body"
    REFERENCES = "references"
    RELATED_ITEMS = "related_items"
