"""MINIO archive domain contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.library.domain.types.minio_archive_payload_types import (
    MinioArchiveDetailsPayload,
)


@dataclass(frozen=True, slots=True)
class MinioArchiveItem:
    """Library-owned read model for a MINIO-backed archive item."""

    id: str
    item_type: ItemType
    title: str
    summary: str
    content: str
    category_id: str | None
    tags: list[str]
    status: ItemStatus
    source_type: SourceType
    created_by_type: CreatedByType
    created_by_name: str
    details: MinioArchiveDetailsPayload
    created_at: datetime
    updated_at: datetime
    is_archived: bool
