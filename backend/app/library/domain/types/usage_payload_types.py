"""Usage domain payload contracts."""

from __future__ import annotations

from datetime import datetime

from app.library.domain.event_enum.usage_enums import SelectionSource
from app.shared.types.extra_types import JSONValue
from typing_extensions import TypedDict


class UsageFeedbackPayload(TypedDict, extra_items=JSONValue):
    """Arbitrary JSON feedback object attached to a usage event."""


class UsageRecordCommandPayload(TypedDict, closed=True):
    """Application command payload for recording one usage event."""

    item_id: str
    item_type: str
    agent_name: str
    librarian_provider: str | None
    query: str | None
    selection_source: SelectionSource
    used_at: datetime
    success: bool
    feedback: str | UsageFeedbackPayload | None


class UsageCreateRecord(TypedDict, closed=True):
    """Persistence record for creating one usage event."""

    item_id: str
    item_type: str
    agent_name: str
    librarian_provider: str | None
    query: str | None
    selection_source: str
    used_at: datetime
    success: bool
    feedback: UsageFeedbackPayload | None


class UsageRecordPayload(TypedDict, closed=True):
    """API-safe usage event payload returned by application services."""

    id: str
    item_id: str
    item_type: str
    agent_name: str
    librarian_provider: str | None
    selection_source: SelectionSource
    used_at: datetime
    success: bool


class PopularItemPayload(TypedDict, closed=True):
    """Usage count payload for one library item."""

    item_id: str
    count: int


class PopularByCategoryPayload(TypedDict, closed=True):
    """Usage count payload grouped by category and item type."""

    category_id: str
    item_type: str
    count: int


type UsageRecordPayloadList = list[UsageRecordPayload]
type PopularItemPayloadList = list[PopularItemPayload]
type PopularByCategoryPayloadList = list[PopularByCategoryPayload]
type PopularItemRows = list[tuple[str, int]]
type PopularByCategoryRows = list[tuple[str, str, int]]
