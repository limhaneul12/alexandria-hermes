"""Contracts proving legacy WORKFLOW library surfaces stay removed."""

from __future__ import annotations

import pytest
from app.library.domain.event_enum.item_enums import ItemType
from app.library.interface.schemas.item.item_schema import ItemCreateRequest
from app.main import app
from pydantic import ValidationError


def test_workflow_routes_are_not_registered() -> None:
    """The unused workflow CRUD router must not remain in the public API."""
    workflow_paths = [
        path for path in app.openapi()["paths"] if path.startswith("/library/workflows")
    ]

    assert workflow_paths == []


def test_library_item_type_excludes_workflow() -> None:
    """Generic library item contracts should not accept WORKFLOW as an item type."""
    item_type_values = {item_type.value for item_type in ItemType}

    assert item_type_values == {"SKILL", "PROMPT"}


@pytest.mark.parametrize("raw_item_type", ["WORKFLOW", "workflow"])
def test_generic_item_create_rejects_workflow_item_type(raw_item_type: str) -> None:
    """Generic item creation must not be a backdoor for removed workflow items."""
    with pytest.raises(ValidationError):
        ItemCreateRequest.model_validate(
            {
                "item_type": raw_item_type,
                "title": "Removed workflow",
                "content": "This concept is no longer a library item type.",
                "created_by_type": "USER",
                "created_by_name": "alex",
            }
        )
