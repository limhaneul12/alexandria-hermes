"""Item-family router contract tests for strict JSON boundaries."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from tests.library.interface.provider_overrides import override_library_provider
from app.main import app
from app.shared.types.extra_types import JSONValue
from fastapi.testclient import TestClient


_CREATED_AT = datetime(2026, 5, 12, 10, 0, tzinfo=UTC)
_UPDATED_AT = datetime(2026, 5, 12, 10, 5, tzinfo=UTC)
_RELATED_ID = "00000000-0000-4000-8000-000000000010"


def _item_payload(
    *,
    item_type: str,
    title: str,
    content: str,
    details: dict[str, JSONValue],
    status: object,
) -> dict[str, JSONValue]:
    """Build a canonical item response payload."""
    return {
        "id": "00000000-0000-4000-8000-000000000777",
        "item_type": item_type,
        "title": title,
        "summary": None,
        "content": content,
        "category_id": None,
        "tags": ["strict-json"],
        "status": status,
        "source_type": "USER_CREATED",
        "created_by_type": "USER",
        "created_by_name": "alex",
        "details": details,
        "created_at": _CREATED_AT,
        "updated_at": _UPDATED_AT,
    }


class FakeKnowledgeService:
    """Knowledge service fake capturing public request values."""

    def __init__(self) -> None:
        """Initialize captured state."""
        self.related_items: list[str] | None = None

    async def create_knowledge(self, **kwargs: Any) -> dict[str, JSONValue]:
        """Return a created knowledge item."""
        self.related_items = kwargs["related_items"]
        return _item_payload(
            item_type="KNOWLEDGE",
            title=str(kwargs["title"]),
            content=str(kwargs["content"]),
            details={
                "body": kwargs["body"],
                "references": kwargs["references"],
                "related_items": kwargs["related_items"],
            },
            status=kwargs["status"],
        )

    async def patch_knowledge(
        self,
        *,
        item_id: str,
        payload: dict[str, JSONValue],
    ) -> dict[str, JSONValue]:
        """Return a patched knowledge item."""
        self.related_items = payload["related_items"]
        return _item_payload(
            item_type="KNOWLEDGE",
            title="Patched knowledge",
            content="Updated content",
            details={"related_items": payload["related_items"]},
            status=payload["status"],
        )


class FakeWorkflowService:
    """Workflow service fake capturing public request values."""

    def __init__(self) -> None:
        """Initialize captured state."""
        self.related_skill_ids: list[str] | None = None

    async def create_workflow(self, **kwargs: Any) -> dict[str, JSONValue]:
        """Return a created workflow item."""
        self.related_skill_ids = kwargs["related_skill_ids"]
        return _item_payload(
            item_type="WORKFLOW",
            title=str(kwargs["title"]),
            content=str(kwargs["content"]),
            details={
                "steps": kwargs["steps"],
                "related_skill_ids": kwargs["related_skill_ids"],
                "expected_result": kwargs["expected_result"],
                "use_case": kwargs["use_case"],
            },
            status=kwargs["status"],
        )

    async def patch_workflow(
        self,
        *,
        item_id: str,
        payload: dict[str, JSONValue],
    ) -> dict[str, JSONValue]:
        """Return a patched workflow item."""
        self.related_skill_ids = payload["related_skill_ids"]
        return _item_payload(
            item_type="WORKFLOW",
            title="Patched workflow",
            content="Updated content",
            details={"related_skill_ids": payload["related_skill_ids"]},
            status=payload["status"],
        )


def test_create_knowledge_accepts_json_status_and_string_related_item_ids() -> None:
    """POST /library/knowledge should accept public enum strings and string item IDs."""
    service = FakeKnowledgeService()

    def override_knowledge_service() -> FakeKnowledgeService:
        return service

    with override_library_provider("knowledge_service", override_knowledge_service()):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/library/knowledge",
                json={
                    "title": "Strict JSON knowledge",
                    "content": "Keep item IDs as strings.",
                    "body": "Strict schemas should accept public string IDs.",
                    "references": ["README.md"],
                    "related_items": [_RELATED_ID],
                    "created_by_name": "alex",
                    "status": "DRAFT",
                    "tags": ["strict-json"],
                },
            )

    assert response.status_code == 201
    assert response.json()["details"]["related_items"] == [_RELATED_ID]
    assert response.json()["status"] == "DRAFT"
    assert service.related_items == [_RELATED_ID]


def test_patch_knowledge_accepts_json_status_and_string_related_item_ids() -> None:
    """PATCH /library/knowledge/{id} should accept enum strings and string related IDs."""
    service = FakeKnowledgeService()

    def override_knowledge_service() -> FakeKnowledgeService:
        return service

    with override_library_provider("knowledge_service", override_knowledge_service()):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.patch(
                "/library/knowledge/00000000-0000-4000-8000-000000000777",
                json={"status": "ACTIVE", "related_items": [_RELATED_ID]},
            )

    assert response.status_code == 200
    assert response.json()["details"]["related_items"] == [_RELATED_ID]
    assert response.json()["status"] == "ACTIVE"
    assert service.related_items == [_RELATED_ID]


def test_create_workflow_accepts_json_status_and_string_related_skill_ids() -> None:
    """POST /library/workflows should accept public enum strings and string skill IDs."""
    service = FakeWorkflowService()

    def override_workflow_service() -> FakeWorkflowService:
        return service

    with override_library_provider("workflow_service", override_workflow_service()):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/library/workflows",
                json={
                    "title": "Strict JSON workflow",
                    "content": "Review string IDs.",
                    "steps": ["Inspect", "Patch"],
                    "related_skill_ids": [_RELATED_ID],
                    "created_by_name": "alex",
                    "status": "DRAFT",
                    "tags": ["strict-json"],
                },
            )

    assert response.status_code == 201
    assert response.json()["details"]["related_skill_ids"] == [_RELATED_ID]
    assert response.json()["status"] == "DRAFT"
    assert service.related_skill_ids == [_RELATED_ID]


def test_patch_workflow_accepts_json_status_and_string_related_skill_ids() -> None:
    """PATCH /library/workflows/{id} should accept enum strings and string skill IDs."""
    service = FakeWorkflowService()

    def override_workflow_service() -> FakeWorkflowService:
        return service

    with override_library_provider("workflow_service", override_workflow_service()):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.patch(
                "/library/workflows/00000000-0000-4000-8000-000000000777",
                json={"status": "ACTIVE", "related_skill_ids": [_RELATED_ID]},
            )

    assert response.status_code == 200
    assert response.json()["details"]["related_skill_ids"] == [_RELATED_ID]
    assert response.json()["status"] == "ACTIVE"
    assert service.related_skill_ids == [_RELATED_ID]
