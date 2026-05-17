"""Read models for thin library candidate search."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.library.domain.event_enum.item_enums import ItemStatus, ItemType
from app.library.domain.types.item_search_payload_types import ItemSearchHitPayload
from app.shared.types.extra_types import JSONObject


@dataclass(frozen=True, slots=True)
class ItemSearchHit:
    """Candidate projection for broad library search."""

    id: str
    item_type: ItemType
    title: str
    summary: str | None
    tags: list[str]
    status: ItemStatus
    category_id: str | None
    score: float
    why_matched: list[str]
    highlights: list[str]
    details_preview: JSONObject
    content_char_count: int
    updated_at: datetime

    def to_payload(self) -> ItemSearchHitPayload:
        """Return the search-hit API payload.

        Returns:
            ItemSearchHitPayload: Candidate payload without full item content.
        """
        payload: ItemSearchHitPayload = {
            "id": self.id,
            "item_type": self.item_type,
            "title": self.title,
            "summary": self.summary,
            "tags": list(self.tags),
            "status": self.status,
            "category_id": self.category_id,
            "score": self.score,
            "why_matched": list(self.why_matched),
            "highlights": list(self.highlights),
            "details_preview": dict(self.details_preview),
            "content_char_count": self.content_char_count,
            "updated_at": self.updated_at,
        }
        return payload


@dataclass(frozen=True, slots=True)
class ItemSearchCandidate:
    """Repository candidate row before query-specific explanation is added."""

    id: str
    item_type: ItemType
    title: str
    summary: str | None
    category_id: str | None
    tags: list[str]
    status: ItemStatus
    details: JSONObject
    content_char_count: int
    updated_at: datetime
    score: float
