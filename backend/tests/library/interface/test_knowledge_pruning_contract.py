"""Contracts proving KNOWLEDGE library item family stays removed."""

from __future__ import annotations

import pytest
from app.library.domain.event_enum.item_enums import ItemType
from app.library.interface.schemas.item.item_schema import ItemCreateRequest
from app.main import app
from fastapi.testclient import TestClient
from pydantic import ValidationError


def test_library_item_type_excludes_knowledge() -> None:
    """Library item types should stay limited to agent capabilities and prompts."""
    item_type_values = {item_type.value for item_type in ItemType}

    assert item_type_values == {"SKILL", "PROMPT"}


@pytest.mark.parametrize("raw_item_type", ["KNOWLEDGE", "knowledge"])
def test_generic_item_create_rejects_knowledge_item_type(raw_item_type: str) -> None:
    """Generic item creation must not be a backdoor for Context Vault knowledge."""
    with pytest.raises(ValidationError):
        ItemCreateRequest.model_validate(
            {
                "item_type": raw_item_type,
                "title": "Removed knowledge item",
                "content": "Durable knowledge belongs in Context Vault.",
                "created_by_type": "AGENT",
                "created_by_name": "alex",
            }
        )


@pytest.mark.parametrize(
    "path",
    [
        "/library/knowledge",
        "/library/knowledge/00000000-0000-4000-8000-000000000777",
    ],
)
def test_library_knowledge_routes_are_not_registered(path: str) -> None:
    """Dedicated KNOWLEDGE item routes should be removed from the API surface."""
    assert path not in app.openapi()["paths"]


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/library/knowledge"),
        ("GET", "/library/knowledge/00000000-0000-4000-8000-000000000777"),
        ("PATCH", "/library/knowledge/00000000-0000-4000-8000-000000000777"),
        ("DELETE", "/library/knowledge/00000000-0000-4000-8000-000000000777"),
    ],
)
def test_library_knowledge_routes_return_404(method: str, path: str) -> None:
    """Removed KNOWLEDGE routes should fail before reaching item services."""
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.request(method, path, json={"title": "Removed"})

    assert response.status_code == 404
