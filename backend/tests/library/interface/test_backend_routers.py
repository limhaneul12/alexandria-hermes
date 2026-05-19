"""Targeted router-level tests for the cleaned API paths."""

from __future__ import annotations

from app.main import app
from fastapi.testclient import TestClient


def test_librarian_classify_returns_typed_labels() -> None:
    """Classify endpoint should resolve the expected taxonomy label."""
    with TestClient(app) as client:
        response = client.post(
            "/librarians/classify", json={"text": "build a reusable API skill"}
        )

    assert response.status_code == 200
    assert response.json()["label"] == "SKILL"


def test_patch_skill_with_empty_payload_returns_400() -> None:
    """Patch endpoints should reject empty update payloads."""
    with TestClient(app) as client:
        response = client.patch("/library/skills/1", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "No fields provided"


def test_list_items_rejects_invalid_item_type_value() -> None:
    """Item list endpoint should validate item_type against the ItemType enum."""
    with TestClient(app) as client:
        response = client.get("/library/items?item_type=INVALID")

    assert response.status_code == 422
