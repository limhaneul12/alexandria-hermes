"""Category router contract tests for folder creation."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.library.domain.entities.read_models import Category
from app.main import app
from tests.shared.provider_overrides import override_library_provider

_CREATED_AT = datetime(2026, 5, 12, 10, 0, tzinfo=UTC)


class _FakeCategoryService:
    """In-memory category service boundary for router contract tests."""

    def __init__(self) -> None:
        self.created_name: str | None = None
        self.created_parent_id: str | None = None

    async def create_category(
        self, *, name: str, parent_id: str | None = None
    ) -> Category:
        """Return one created folder-like category."""
        self.created_name = name
        self.created_parent_id = parent_id
        return Category(
            id="00000000-0000-4000-8000-000000000101",
            name=name,
            parent_id=parent_id,
            position=0,
            created_at=_CREATED_AT,
            updated_at=_CREATED_AT,
        )


def test_create_category_registers_folder_with_optional_parent() -> None:
    """POST /library/categories should create a folder/category for the library shelf."""
    service = _FakeCategoryService()

    def override_category_service() -> _FakeCategoryService:
        return service

    with override_library_provider("category_service", override_category_service()):
        with TestClient(app) as client:
            response = client.post(
                "/library/categories",
                json={
                    "name": "Backend 사서 폴더",
                    "parent_id": "00000000-0000-4000-8000-000000000001",
                },
            )

    assert response.status_code == 201
    assert response.json() == {
        "id": "00000000-0000-4000-8000-000000000101",
        "name": "Backend 사서 폴더",
        "parent_id": "00000000-0000-4000-8000-000000000001",
        "position": 0,
        "created_at": "2026-05-12T10:00:00Z",
        "updated_at": "2026-05-12T10:00:00Z",
    }
    assert service.created_name == "Backend 사서 폴더"
    assert service.created_parent_id == "00000000-0000-4000-8000-000000000001"
