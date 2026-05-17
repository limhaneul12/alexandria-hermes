"""ORM models for Memory Compact artifacts."""

from __future__ import annotations

from datetime import datetime

from app.memory.domain.event_enum.memory_compact_enums import (
    MemoryCompactStatus,
)
from app.shared.infrastructure.database import Base
from app.shared.infrastructure.identifiers import ID_LENGTH, new_uuid
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column


def _status_values_sql() -> str:
    return ",".join(f"'{item.value}'" for item in MemoryCompactStatus)


class MemoryCompactORM(Base):
    """Stored Memory Compact row."""

    __tablename__ = "memory_compacts"

    id: Mapped[str] = mapped_column(
        String(ID_LENGTH), primary_key=True, default=new_uuid
    )
    project: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    covered_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    covered_to: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    markdown_body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            f"status IN ({_status_values_sql()})",
            name="ck_memory_compacts_status",
        ),
        Index(
            "uq_memory_compacts_current_project",
            "project",
            unique=True,
            sqlite_where=(
                (status == MemoryCompactStatus.CURRENT.value) & project.is_not(None)
            ),
            postgresql_where=(
                (status == MemoryCompactStatus.CURRENT.value) & project.is_not(None)
            ),
        ),
        Index(
            "uq_memory_compacts_current_default_project",
            "status",
            unique=True,
            sqlite_where=(
                (status == MemoryCompactStatus.CURRENT.value) & project.is_(None)
            ),
            postgresql_where=(
                (status == MemoryCompactStatus.CURRENT.value) & project.is_(None)
            ),
        ),
    )


class MemoryCompactSourceRefORM(Base):
    """Stored Memory Compact source reference row."""

    __tablename__ = "memory_compact_source_refs"

    id: Mapped[str] = mapped_column(
        String(ID_LENGTH), primary_key=True, default=new_uuid
    )
    compact_id: Mapped[str] = mapped_column(
        String(ID_LENGTH),
        ForeignKey("memory_compacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    detail_path: Mapped[str] = mapped_column(String(512), nullable=False)
