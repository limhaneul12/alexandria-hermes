"""Mapping from MINIO metadata to archive contracts."""

from __future__ import annotations

import hashlib

from app.library.domain.contracts.minio_archive_contracts import MinioArchiveItem
from app.library.domain.entities.read_models import LibrarianProvider
from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.library.domain.types.minio_archive_payload_types import (
    MinioArchiveDetailsPayload,
)
from app.platform.storage.minio_types import MinioObject


def map_minio_object_to_archive_item(
    provider: LibrarianProvider,
    bucket: str,
    endpoint: str,
    item: MinioObject,
) -> MinioArchiveItem:
    """Convert MINIO object metadata into a library archive read model.

    Args:
        provider: Librarian provider that owns the MINIO configuration.
        bucket: MINIO bucket containing the object.
        endpoint: MINIO endpoint used for traceable payload details.
        item: Listed MINIO object metadata.

    Returns:
        MinioArchiveItem: Library archive item built from object metadata.
    """
    details: MinioArchiveDetailsPayload = {
        "source": "MINIO",
        "endpoint": endpoint,
        "bucket": bucket,
        "object_key": item.key,
        "size": item.size,
        "etag": item.etag,
        "version": "object",
    }
    archive_item = MinioArchiveItem(
        id=f"minio:{provider.id}:{hashlib.sha256(item.key.encode()).hexdigest()[:16]}",
        item_type=ItemType.KNOWLEDGE,
        title=_object_title(item.key),
        summary=f"MINIO object from {bucket}",
        content=f"s3://{bucket}/{item.key}",
        category_id=None,
        tags=["minio", bucket],
        status=ItemStatus.ACTIVE,
        source_type=SourceType.IMPORTED,
        created_by_type=CreatedByType.LIBRARIAN,
        created_by_name=provider.name,
        details=details,
        created_at=item.last_modified,
        updated_at=item.last_modified,
        is_archived=False,
    )
    return archive_item


def _object_title(key: str) -> str:
    clean_key = key.rstrip("/")
    title = clean_key.rsplit("/", 1)[-1] or clean_key or "MINIO object"
    return title
