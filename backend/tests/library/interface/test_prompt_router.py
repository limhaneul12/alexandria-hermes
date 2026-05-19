"""Prompt router contract tests."""

from __future__ import annotations

from datetime import UTC, datetime

from app.library.application.item_service import ItemService
from app.library.application.prompt_service import PromptService
from app.library.domain.contracts.item_contracts import ItemCreate, ItemUpdate
from app.library.domain.entities.item_search_hit import ItemSearchCandidate
from app.library.domain.entities.item_search_query import ItemSearchQuery
from app.library.domain.entities.read_models import LibraryItem
from app.library.domain.event_enum.item_enums import ItemType
from app.library.domain.repositories.item_repository import IItemRepository
from app.main import app
from app.shared.types.extra_types import JSONValue
from fastapi.testclient import TestClient
from tests.shared.provider_overrides import override_library_provider


class FakeItemRepository(IItemRepository):
    """In-memory item repository for prompt router tests."""

    def __init__(self) -> None:
        """Initialize captured payload state."""
        self.created_payload: dict[str, JSONValue] | None = None

    async def create(self, *, payload: ItemCreate) -> LibraryItem:
        """Create one prompt item."""
        self.created_payload = payload.to_record()
        return LibraryItem(
            id="00000000-0000-4000-8000-000000000321",
            item_type=payload.item_type.value,
            title=payload.title,
            summary=payload.summary,
            content=payload.content,
            category_id=payload.category_id,
            tags=payload.tags,
            status=payload.status.value,
            source_type=payload.source_type.value,
            created_by_type=payload.created_by_type,
            created_by_name=payload.created_by_name,
            details=payload.details,
            created_at=datetime(2026, 5, 14, 10, 0, tzinfo=UTC),
            updated_at=datetime(2026, 5, 14, 10, 5, tzinfo=UTC),
            is_archived=False,
        )

    async def update(self, item_id: str, *, payload: ItemUpdate) -> LibraryItem:
        """Update is unused by these tests."""
        raise AssertionError("update should not be called")

    async def get(self, item_id: str) -> LibraryItem | None:
        """Get is unused by these tests."""
        return None

    async def delete(self, item_id: str) -> None:
        """Delete is unused by these tests."""

    async def list_by_type(
        self,
        *,
        item_type: ItemType,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[LibraryItem]:
        """List by type is unused by these tests."""
        return []

    async def list_all(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
        category_id: str | None = None,
        search_query: str | None = None,
    ) -> tuple[list[LibraryItem], int]:
        """List all is unused by these tests."""
        return [], 0

    async def search(
        self, query: str, item_type: ItemType | None = None
    ) -> list[LibraryItem]:
        """Search is unused by these tests."""
        return []

    async def search_candidates(
        self,
        options: ItemSearchQuery,
    ) -> tuple[list[ItemSearchCandidate], int]:
        """Candidate search is unused by these tests."""
        return [], 0


def test_submit_prompt_by_agent_records_agent_authored_prompt() -> None:
    """POST /library/prompts/submit-by-agent should be the prompt create path."""
    item_repo = FakeItemRepository()

    def override_prompt_service() -> PromptService:
        return PromptService(item_service=ItemService(item_repo=item_repo))

    with (
        override_library_provider("prompt_service", override_prompt_service()),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post(
            "/library/prompts/submit-by-agent",
            json={
                "title": "Agent-authored prompt",
                "summary": "Generated from agent prompt work.",
                "content": "Summarize this context: {{context}}",
                "category_id": "00000000-0000-4000-8000-000000000002",
                "tags": ["agent", "prompt"],
                "content_format": "MARKDOWN",
                "prompt_kind": "USER_TEMPLATE",
                "prompt_domain": "DEVELOPMENT",
                "prompt_task_type": "DOCUMENT_SUMMARY",
                "input_variables": [{"name": "context", "required": True}],
                "created_by_name": "prompt-agent",
                "status": "ACTIVE",
            },
        )

    assert response.status_code == 201
    assert response.json()["item_type"] == "PROMPT"
    assert response.json()["source_type"] == "AGENT_SUBMITTED"
    assert response.json()["created_by_type"] == "AGENT"
    assert response.json()["created_by_name"] == "prompt-agent"
    assert item_repo.created_payload is not None
    assert item_repo.created_payload["source_type"] == "AGENT_SUBMITTED"
    assert item_repo.created_payload["created_by_type"] == "AGENT"
