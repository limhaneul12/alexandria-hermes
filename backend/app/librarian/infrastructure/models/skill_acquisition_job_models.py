"""ORM model for durable skill-acquisition jobs."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.librarian.domain.event_enum.collaboration_enums import (
    SkillAcquisitionJobStatus,
)
from app.shared.infrastructure.database import Base
from app.shared.infrastructure.datetime_types import UTCDateTime
from app.shared.infrastructure.identifiers import ID_LENGTH
from app.shared.types.extra_types import JSONObject


class SkillAcquisitionJobORM(Base):
    """Durable local job for background skill acquisition."""

    __tablename__ = "skill_acquisition_jobs"

    id: Mapped[str] = mapped_column(String(ID_LENGTH), primary_key=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    agent_name: Mapped[str] = mapped_column(String(255), nullable=False)
    project: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    task_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    provider_id: Mapped[str | None] = mapped_column(String(ID_LENGTH), nullable=True)
    librarian_profile_id: Mapped[str | None] = mapped_column(
        String(ID_LENGTH), nullable=True
    )
    skill_id: Mapped[str | None] = mapped_column(String(ID_LENGTH), nullable=True)
    context_id: Mapped[str | None] = mapped_column(String(ID_LENGTH), nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_urls: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    progress_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    skill_note_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    reindex_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verification_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    handoff: Mapped[JSONObject | None] = mapped_column(JSON, nullable=True)
    repair_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    search_snapshot: Mapped[JSONObject | None] = mapped_column(JSON, nullable=True)
    acquisition_override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prompt_reference_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN "
            f"({','.join(f"'{status.value}'" for status in SkillAcquisitionJobStatus)})",
            name="ck_skill_acquisition_jobs_status",
        ),
    )
