"""MINIO-backed archive item response schemas."""

from __future__ import annotations

from app.library.domain.contracts.minio_archive_contracts import MinioArchiveItem
from app.library.domain.contracts.minio_import_contracts import (
    MinioImportCandidate,
    MinioImportResult,
)
from app.library.domain.event_enum.item_enums import ItemType
from app.library.interface.schemas._types import StrictRootSchema, StrictSchema
from app.library.interface.schemas.item.item_schema import ItemResponse
from app.shared.types.extra_types import JSONValue
from pydantic import ConfigDict, Field, field_validator


class MinioArchiveItemResponse(ItemResponse):
    """Response schema for MINIO-backed archive items."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "minio:provider-1:7f9d5c0e3b2a1d4c",
                    "item_type": "KNOWLEDGE",
                    "title": "a.md",
                    "summary": "MINIO object from archive",
                    "content": "s3://archive/skills/a.md",
                    "category_id": None,
                    "tags": ["minio", "archive"],
                    "status": "ACTIVE",
                    "source_type": "IMPORTED",
                    "created_by_type": "LIBRARIAN",
                    "created_by_name": "local minio",
                    "details": {
                        "source": "MINIO",
                        "endpoint": "https://objects.example.com",
                        "bucket": "archive",
                        "object_key": "skills/a.md",
                        "size": 7,
                        "etag": "etag-1",
                        "version": "object",
                    },
                    "created_at": "2026-01-02T00:00:00Z",
                    "updated_at": "2026-01-02T00:00:00Z",
                }
            ]
        }
    )

    @classmethod
    def from_archive_item(
        cls,
        archive_item: MinioArchiveItem,
    ) -> MinioArchiveItemResponse:
        """Create a public response from an application read model.

        Args:
            archive_item [MinioArchiveItem]: Value supplied to from_archive_item.

        Returns:
            MinioArchiveItemResponse: Value produced by from_archive_item.
        """
        response = cls(
            id=archive_item.id,
            item_type=archive_item.item_type,
            title=archive_item.title,
            summary=archive_item.summary,
            content=archive_item.content,
            category_id=archive_item.category_id,
            tags=archive_item.tags,
            status=archive_item.status,
            source_type=archive_item.source_type,
            created_by_type=archive_item.created_by_type.value,
            created_by_name=archive_item.created_by_name,
            details=archive_item.details,
            created_at=archive_item.created_at,
            updated_at=archive_item.updated_at,
        )
        return response


class MinioArchiveItemResponseList(StrictRootSchema[list[MinioArchiveItemResponse]]):
    """Root response schema for MINIO archive item arrays."""

    @classmethod
    def from_archive_items(
        cls,
        archive_items: list[MinioArchiveItem],
    ) -> MinioArchiveItemResponseList:
        """Create a public root response from application read models.

        Args:
            archive_items [list[MinioArchiveItem]]: Value supplied to from_archive_items.

        Returns:
            MinioArchiveItemResponseList: Value produced by from_archive_items.
        """
        responses = [
            MinioArchiveItemResponse.from_archive_item(item) for item in archive_items
        ]
        validation = cls.model_validate(responses)
        return validation


class MinioImportCandidateResponse(StrictSchema):
    """Response schema for one external archive import candidate."""

    id: str
    provider_id: str
    bucket: str
    object_key: str
    title: str
    summary: str
    content_preview: str
    item_type: ItemType
    tags: list[str]
    details: dict[str, JSONValue]
    confidence: float = Field(ge=0.0, le=1.0)
    needs_review: bool

    @field_validator("item_type", mode="before")
    @classmethod
    def parse_item_type(cls, value: ItemType | str) -> ItemType:
        """Parse candidate item type values.

        Args:
            value: Raw enum or string from validation.

        Returns:
            Parsed item type enum.
        """
        if isinstance(value, ItemType):
            return value
        parsed = ItemType(value)
        return parsed

    @classmethod
    def from_candidate(
        cls,
        candidate: MinioImportCandidate,
    ) -> MinioImportCandidateResponse:
        """Create a public response from an import candidate.

        Args:
            candidate: Application import candidate.

        Returns:
            Public candidate response.
        """
        response = cls(
            id=candidate.id,
            provider_id=candidate.provider_id,
            bucket=candidate.bucket,
            object_key=candidate.object_key,
            title=candidate.title,
            summary=candidate.summary,
            content_preview=candidate.content_preview,
            item_type=candidate.item_type,
            tags=candidate.tags,
            details=candidate.details,
            confidence=candidate.confidence,
            needs_review=candidate.needs_review,
        )
        return response


class MinioImportCandidateResponseList(
    StrictRootSchema[list[MinioImportCandidateResponse]]
):
    """Root response schema for import candidate arrays."""

    @classmethod
    def from_candidates(
        cls,
        candidates: list[MinioImportCandidate],
    ) -> MinioImportCandidateResponseList:
        """Create a public root response from import candidates.

        Args:
            candidates: Application import candidates.

        Returns:
            Public root response containing candidates.
        """
        responses = [
            MinioImportCandidateResponse.from_candidate(item) for item in candidates
        ]
        validation = cls.model_validate(responses)
        return validation


class MinioImportRequest(StrictSchema):
    """Request to import linked external archive objects."""

    limit: int = Field(default=48, ge=1, le=1000)


class MinioImportResultResponse(StrictSchema):
    """Response after importing external archive candidates."""

    imported_count: int
    skipped_count: int
    item_ids: list[str]

    @classmethod
    def from_result(cls, result: MinioImportResult) -> MinioImportResultResponse:
        """Create public response from import result.

        Args:
            result: Application import result.

        Returns:
            Public import result response.
        """
        response = cls(
            imported_count=result.imported_count,
            skipped_count=result.skipped_count,
            item_ids=result.item_ids,
        )
        return response
