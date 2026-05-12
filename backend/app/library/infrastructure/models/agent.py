"""ORM model for external agents consuming the library."""

from __future__ import annotations

from datetime import datetime

from app.shared.infrastructure.database import Base
from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class AgentProfileORM(Base):
    """Profile record for user/agent identities using Alexandria Hermes."""

    __tablename__ = "agent_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    capabilities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    preferred_librarian_provider: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def __repr__(self) -> str:
        return f"AgentProfileORM(id={self.id!r}, name={self.name!r})"
