"""Contracts for importing external MINIO archive objects."""

from __future__ import annotations

from dataclasses import dataclass

from app.library.domain.event_enum.item_enums import ItemType
from app.shared.types.extra_types import JSONObject


@dataclass(frozen=True, slots=True)
class MinioImportCandidate:
    """Candidate library card inferred from one external MINIO object."""

    id: str
    provider_id: str
    bucket: str
    object_key: str
    title: str
    summary: str
    content_preview: str
    item_type: ItemType
    tags: list[str]
    details: JSONObject
    confidence: float
    needs_review: bool


@dataclass(frozen=True, slots=True)
class MinioImportResult:
    """Result of importing one or more MINIO candidates into the DB catalog."""

    imported_count: int
    skipped_count: int
    item_ids: list[str]
