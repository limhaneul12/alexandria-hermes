"""Skill payload mapping behavior tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.library.application.skills.payload_mapper import (
    build_librarian_skill_item_payload,
    build_skill_details,
    shape_skill_patch_payload,
)
from app.library.domain.contracts.librarian_candidate_contracts import (
    CreateSkillCandidateResult,
)
from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.library.domain.event_enum.skill_enums import RiskLevel
from app.library.domain.types.item_payload_types import LibraryItemPayload
from app.shared.exceptions import ValidationError
from app.shared.types.extra_types import JSONObject, JSONValue


def _skill_item_payload(details: JSONObject) -> LibraryItemPayload:
    """Build a typed skill item payload for patch-shaping tests.

    Args:
        details: Existing item details.

    Returns:
        LibraryItemPayload: Typed skill payload.
    """
    now = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)
    item_payload: LibraryItemPayload = {
        "id": "00000000-0000-4000-8000-000000000010",
        "item_type": ItemType.SKILL,
        "title": "Existing skill",
        "summary": "Existing summary",
        "content": "Existing content",
        "category_id": None,
        "tags": ["skill"],
        "status": ItemStatus.ACTIVE,
        "source_type": SourceType.USER_CREATED,
        "created_by_type": CreatedByType.USER,
        "created_by_name": "test-user",
        "details": details,
        "created_at": now,
        "updated_at": now,
    }
    return item_payload


def test_build_skill_details_preserves_skill_contract_fields() -> None:
    """Skill details mapper should keep the public detail contract unchanged."""
    details = build_skill_details(
        purpose="Automate review steps.",
        input_schema={"type": "object"},
        output_schema={"type": "object", "required": ["result"]},
        usage_example=None,
        required_tools=["pytest"],
        risk_level="LOW",
        version="1.0.0",
    )

    assert details == {
        "purpose": "Automate review steps.",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object", "required": ["result"]},
        "usage_example": None,
        "required_tools": ["pytest"],
        "risk_level": "LOW",
        "version": "1.0.0",
    }


def test_build_librarian_skill_item_payload_preserves_typed_candidate_fields() -> None:
    """Librarian candidate mapper should preserve typed generated values."""
    generated = CreateSkillCandidateResult(
        title="Generated FastAPI skill",
        summary="Generated summary",
        content="Generated content",
        purpose="Generated purpose",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        required_tools=["planner"],
        risk_level=RiskLevel.LOW,
        version="1.0.0",
        provider_id="provider-123",
        prompt="Create a skill.",
    )

    payload = build_librarian_skill_item_payload(
        generated=generated,
        category_id="category-123",
        tags=["generated"],
        created_by_name="librarian",
    )

    assert payload == {
        "title": "Generated FastAPI skill",
        "summary": "Generated summary",
        "content": "Generated content",
        "category_id": "category-123",
        "tags": ["generated"],
        "details": {
            "purpose": "Generated purpose",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "usage_example": None,
            "required_tools": ["planner"],
            "risk_level": "LOW",
            "version": "1.0.0",
            "librarian_provider_id": "provider-123",
            "prompt": "Create a skill.",
        },
    }


def test_shape_skill_patch_payload_merges_base_and_detail_fields() -> None:
    """Patch shaping should merge skill detail updates into existing details."""
    existing_item = _skill_item_payload(
        {
            "purpose": "Old purpose",
            "risk_level": "LOW",
            "version": "1.0.0",
        }
    )
    payload: dict[str, JSONValue] = {
        "summary": "Updated summary",
        "required_tools": ["pytest", "httpx"],
        "version": "1.0.1",
        "unknown": "ignored",
    }

    shaped_payload = shape_skill_patch_payload(item=existing_item, payload=payload)

    assert shaped_payload == {
        "summary": "Updated summary",
        "details": {
            "purpose": "Old purpose",
            "risk_level": "LOW",
            "version": "1.0.1",
            "required_tools": ["pytest", "httpx"],
        },
    }
    assert existing_item["details"] == {
        "purpose": "Old purpose",
        "risk_level": "LOW",
        "version": "1.0.0",
    }


@pytest.mark.parametrize("payload", [{}, {"unknown": "ignored"}])
def test_shape_skill_patch_payload_rejects_empty_effective_updates(
    payload: dict[str, JSONValue],
) -> None:
    """Patch shaping should reject payloads with no supported patch fields."""
    with pytest.raises(ValidationError, match="No fields provided"):
        shape_skill_patch_payload(
            item=_skill_item_payload({"purpose": "Old purpose"}),
            payload=payload,
        )


def test_shape_skill_patch_payload_keeps_enum_base_field_values() -> None:
    """Patch shaping should pass through supported base field values unchanged."""
    shaped_payload = shape_skill_patch_payload(
        item=_skill_item_payload({}),
        payload={"status": ItemStatus.ACTIVE},
    )

    assert shaped_payload == {"status": ItemStatus.ACTIVE}
