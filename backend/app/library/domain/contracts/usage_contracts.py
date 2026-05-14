"""Usage repository command contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.library.domain.event_enum.usage_enums import SelectionSource
from app.library.domain.types.usage_payload_types import (
    UsageCreateRecord,
    UsageFeedbackPayload,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class UsageCreate:
    """Fields required to persist a usage event."""

    item_id: str
    item_type: str
    agent_name: str
    librarian_provider: str | None
    query: str | None
    selection_source: SelectionSource
    used_at: datetime
    success: bool
    feedback: UsageFeedbackPayload | None

    def to_record(self) -> UsageCreateRecord:
        """Return persistence fields for SQLAlchemy model construction.

        Returns:
            UsageCreateRecord: Persistence record for usage event creation.
        """
        record: UsageCreateRecord = {
            "item_id": self.item_id,
            "item_type": self.item_type,
            "agent_name": self.agent_name,
            "librarian_provider": self.librarian_provider,
            "query": self.query,
            "selection_source": self.selection_source.value,
            "used_at": self.used_at,
            "success": self.success,
            "feedback": self.feedback,
        }
        return record
