"""ORM models for the rebuildable Obsidian index cache."""

from __future__ import annotations

from datetime import datetime

from app.shared.infrastructure.database import Base
from app.shared.infrastructure.datetime_types import UTCDateTime
from app.shared.infrastructure.identifiers import new_uuid
from app.shared.types.extra_types import JSONValue
from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column


class ObsidianFileORM(Base):
    """Indexed Obsidian Markdown note metadata."""

    __tablename__ = "obsidian_files"

    note_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    relative_path: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    alexandria_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    project: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    frontmatter_json: Mapped[dict[str, JSONValue]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    index_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    modified_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    indexed_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)

    __table_args__ = (UniqueConstraint("relative_path", name="uq_obsidian_files_path"),)


class ObsidianChunkORM(Base):
    """Indexed text chunk for one Obsidian note."""

    __tablename__ = "obsidian_chunks"

    id: Mapped[str] = mapped_column(String(255), primary_key=True, default=new_uuid)
    note_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("obsidian_files.note_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    heading_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class ObsidianEdgeORM(Base):
    """Indexed graph edge derived from canonical Markdown."""

    __tablename__ = "obsidian_edges"

    edge_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_note_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("obsidian_files.note_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_path: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    target_note_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    target_path: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    relation: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source_kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    indexed_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class ObsidianLibrarianWorkflowORM(Base):
    """Persisted checkpoint for an Obsidian librarian workflow."""

    __tablename__ = "obsidian_librarian_workflows"

    thread_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    active_note_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    project: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    provider_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delegate_requested: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    state_json: Mapped[dict[str, JSONValue]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
