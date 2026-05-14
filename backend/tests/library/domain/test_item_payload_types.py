"""Typed payload contracts for library item read models."""

from __future__ import annotations

from datetime import UTC, datetime

from app.library.domain.entities.read_models import LibraryItem
from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.library.domain.types.item_payload_types import (
    LibraryItemListResult,
    LibraryItemPayload,
)


def _library_item() -> LibraryItem:
    """Build a representative item read model."""
    timestamp = datetime(2026, 5, 14, 12, 30, tzinfo=UTC)
    return LibraryItem(
        id="00000000-0000-4000-8000-000000000101",
        item_type=ItemType.SKILL,
        title="Typed item payloads",
        summary="Use domain-owned TypedDict payloads.",
        content="Promote item payload dictionaries into named contracts.",
        category_id="00000000-0000-4000-8000-000000000202",
        tags=["typing", "ddd"],
        status=ItemStatus.ACTIVE,
        source_type=SourceType.USER_CREATED,
        created_by_type=CreatedByType.USER,
        created_by_name="alex",
        details={"risk_level": "LOW"},
        created_at=timestamp,
        updated_at=timestamp,
        is_archived=False,
    )


def test_library_item_to_dict_returns_domain_typed_payload_with_enums() -> None:
    """LibraryItem should own the shaped API payload projection."""
    item = _library_item()

    payload: LibraryItemPayload = item.to_dict()

    assert payload["id"] == item.id
    assert payload["item_type"] is ItemType.SKILL
    assert payload["status"] is ItemStatus.ACTIVE
    assert payload["source_type"] is SourceType.USER_CREATED
    assert payload["tags"] == ["typing", "ddd"]
    assert payload["tags"] is not item.tags
    assert payload["details"] == {"risk_level": "LOW"}
    assert payload["details"] is not item.details


def test_library_item_list_result_alias_names_paged_payload_contract() -> None:
    """Paged item responses should not use anonymous tuple/list/dict shapes."""
    payload: LibraryItemPayload = _library_item().to_dict()

    result: LibraryItemListResult = ([payload], 1)

    assert result[0] == [payload]
    assert result[1] == 1
