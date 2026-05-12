"""ORM model for hierarchical categories."""

from __future__ import annotations

from datetime import datetime

from app.shared.infrastructure.database import Base
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


class CategoryORM(Base):
    """Hierarchical taxonomy category."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(length=255), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), index=True, nullable=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    parent: Mapped[CategoryORM | None] = relationship(
        "CategoryORM",
        remote_side="CategoryORM.id",
        back_populates="children",
        lazy="joined",
    )
    children: Mapped[list[CategoryORM]] = relationship(
        "CategoryORM",
        back_populates="parent",
        cascade="all, delete-orphan",
        order_by="CategoryORM.position",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"CategoryORM(id={self.id!r}, name={self.name!r})"
