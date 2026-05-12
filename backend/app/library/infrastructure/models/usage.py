"""ORM model for usage history events."""

from __future__ import annotations

from datetime import datetime

from app.shared.infrastructure.database import Base
from app.shared.types.extra_types import JSONValue
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class UsageHistoryORM(Base):
    """Usage history for recommendation and browse tracking."""

    __tablename__ = "usage_histories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("library_items.id", ondelete="CASCADE"), index=True
    )
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(255), nullable=False)
    librarian_provider: Mapped[str | None] = mapped_column(String(255), nullable=True)
    query: Mapped[str | None] = mapped_column(Text, nullable=True)
    selection_source: Mapped[str] = mapped_column(String(24), nullable=False)
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    success: Mapped[bool] = mapped_column(nullable=False)
    feedback: Mapped[dict[str, JSONValue] | None] = mapped_column(JSON, nullable=True)

    @property
    def selection_source_enum(self) -> str:
        return self.selection_source

    def __repr__(self) -> str:
        return f"UsageHistoryORM(id={self.id!r}, item_id={self.item_id!r})"
