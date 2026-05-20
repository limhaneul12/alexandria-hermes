"""ORM model for unified library items."""

from __future__ import annotations

from datetime import datetime

from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.shared.infrastructure.database import Base
from app.shared.infrastructure.datetime_types import UTCDateTime
from app.shared.infrastructure.identifiers import ID_LENGTH, new_uuid
from app.shared.types.extra_types import JSONValue
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column


class LibraryItemORM(Base):
    """Single table for shared library item entries."""

    __tablename__ = "library_items"

    id: Mapped[str] = mapped_column(
        String(ID_LENGTH), primary_key=True, default=new_uuid
    )
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(length=255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category_id: Mapped[str | None] = mapped_column(
        String(ID_LENGTH),
        ForeignKey("categories.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    created_by_type: Mapped[str] = mapped_column(String(20), nullable=False)
    created_by_name: Mapped[str] = mapped_column(String(length=255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    details: Mapped[dict[str, JSONValue]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        CheckConstraint(
            f"item_type IN ({','.join(f"'{i.value}'" for i in ItemType)})",
            name="ck_library_items_type",
        ),
        CheckConstraint(
            f"status IN ({','.join(f"'{i.value}'" for i in ItemStatus)})",
            name="ck_library_items_status",
        ),
        CheckConstraint(
            f"source_type IN ({','.join(f"'{i.value}'" for i in SourceType)})",
            name="ck_library_items_source_type",
        ),
        CheckConstraint(
            f"created_by_type IN ({','.join(f"'{i.value}'" for i in CreatedByType)})",
            name="ck_library_items_created_by_type",
        ),
    )

    def __repr__(self) -> str:
        return f"LibraryItemORM(id={self.id!r}, item_type={self.item_type!r})"
