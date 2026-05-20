"""ORM model for usage history events."""

from __future__ import annotations

from datetime import datetime

from app.shared.infrastructure.database import Base
from app.shared.infrastructure.datetime_types import UTCDateTime
from app.shared.infrastructure.identifiers import ID_LENGTH, new_uuid
from app.shared.types.extra_types import JSONValue
from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class UsageHistoryORM(Base):
    """Usage history for recommendation and browse tracking."""

    __tablename__ = "usage_histories"

    id: Mapped[str] = mapped_column(
        String(ID_LENGTH), primary_key=True, default=new_uuid
    )
    item_id: Mapped[str] = mapped_column(
        String(ID_LENGTH),
        ForeignKey("library_items.id", ondelete="CASCADE"),
        index=True,
    )
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(255), nullable=False)
    librarian_provider: Mapped[str | None] = mapped_column(String(255), nullable=True)
    query: Mapped[str | None] = mapped_column(Text, nullable=True)
    selection_source: Mapped[str] = mapped_column(String(24), nullable=False)
    used_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    success: Mapped[bool] = mapped_column(nullable=False)
    feedback: Mapped[dict[str, JSONValue] | None] = mapped_column(JSON, nullable=True)

    @property
    def selection_source_enum(self) -> str:
        return self.selection_source

    def __repr__(self) -> str:
        return f"UsageHistoryORM(id={self.id!r}, item_id={self.item_id!r})"
