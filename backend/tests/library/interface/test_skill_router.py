"""Skill router contract tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.library.application.item_service import ItemService
from app.library.application.skill_service import SkillService
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
    """In-memory item repository for skill router contract tests."""

    def __init__(self) -> None:
        """Initialize captured payload state."""
        self.created_payload: dict[str, JSONValue] | None = None

    async def create(self, *, payload: ItemCreate) -> LibraryItem:
        """Create one library item."""
        self.created_payload = payload.to_record()
        return LibraryItem(
            id="00000000-0000-4000-8000-000000000123",
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
            created_at=datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
            updated_at=datetime(2026, 5, 12, 10, 5, tzinfo=UTC),
            is_archived=False,
        )

    async def update(
        self,
        item_id: str,
        *,
        payload: ItemUpdate,
    ) -> LibraryItem:
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


def _valid_submit_skill_by_agent_payload() -> dict[str, JSONValue]:
    """Return a valid self-acquired skill submission payload."""
    return {
        "title": "Agent-authored FastAPI skill",
        "purpose": "Capture route testing guidance.",
        "summary": "Generated candidate from an agent.",
        "content": "Use narrow dependency overrides.",
        "category_id": "00000000-0000-4000-8000-000000000002",
        "tags": ["agent", "fastapi"],
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "usage_example": "Submit, review, then activate.",
        "required_tools": ["pytest"],
        "risk_level": "MEDIUM",
        "version": "1.0.0",
        "created_by_name": "research-agent",
        "activate": False,
        "status": "ACTIVE",
    }


def _post_submit_skill_by_agent(
    payload: dict[str, JSONValue],
) -> tuple[int, dict[str, object]]:
    """Post an agent skill submission with an in-memory item boundary fake."""
    item_repo = FakeItemRepository()

    def override_skill_service() -> SkillService:
        return SkillService(item_service=ItemService(item_repo=item_repo))

    with (
        override_library_provider("skill_service", override_skill_service()),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post("/library/skills/submit-by-agent", json=payload)

    return response.status_code, response.json()


def test_create_skill_registers_manual_skill_with_public_json_payload() -> None:
    """POST /library/skills should create a manually registered user skill."""
    item_repo = FakeItemRepository()

    def override_skill_service() -> SkillService:
        return SkillService(item_service=ItemService(item_repo=item_repo))

    with (
        override_library_provider("skill_service", override_skill_service()),
        TestClient(app) as client,
    ):
        response = client.post(
            "/library/skills",
            json={
                "title": "Manual FastAPI skill",
                "summary": "Manual skill registration smoke.",
                "content": "Use narrow dependency overrides.",
                "category_id": "00000000-0000-4000-8000-000000000002",
                "tags": ["fastapi", "manual"],
                "purpose": "Register a reusable skill from the library UI.",
                "input_schema": {},
                "output_schema": {},
                "usage_example": "Fill the form and save the skill.",
                "required_tools": ["pytest"],
                "risk_level": "LOW",
                "version": "1.0.0",
                "created_by_name": "alex",
                "status": "DRAFT",
            },
        )

    assert response.status_code == 201
    assert response.json()["title"] == "Manual FastAPI skill"
    assert response.json()["item_type"] == "SKILL"
    assert response.json()["status"] == "DRAFT"
    assert item_repo.created_payload is not None
    assert item_repo.created_payload["source_type"] == "USER_CREATED"
    assert item_repo.created_payload["created_by_type"] == "USER"


def test_submit_skill_by_agent_accepts_json_enum_values_and_returns_created_skill() -> (
    None
):
    """POST /library/skills/submit-by-agent should accept public JSON enum strings."""
    item_repo = FakeItemRepository()

    def override_skill_service() -> SkillService:
        return SkillService(item_service=ItemService(item_repo=item_repo))

    with (
        override_library_provider("skill_service", override_skill_service()),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post(
            "/library/skills/submit-by-agent",
            json={
                "title": "Agent-authored FastAPI skill",
                "purpose": "Capture route testing guidance.",
                "summary": "Generated candidate from an agent.",
                "content": "Use narrow dependency overrides.",
                "category_id": "00000000-0000-4000-8000-000000000002",
                "tags": ["agent", "fastapi"],
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "usage_example": "Submit, review, then activate.",
                "required_tools": ["pytest"],
                "risk_level": "MEDIUM",
                "version": "1.0.0",
                "created_by_name": "research-agent",
                "activate": False,
                "status": "ACTIVE",
            },
        )

    assert response.status_code == 201
    assert response.json() == {
        "id": "00000000-0000-4000-8000-000000000123",
        "item_type": "SKILL",
        "title": "Agent-authored FastAPI skill",
        "summary": "Generated candidate from an agent.",
        "content": "Use narrow dependency overrides.",
        "category_id": "00000000-0000-4000-8000-000000000002",
        "tags": ["agent", "fastapi"],
        "status": "ACTIVE",
        "source_type": "AGENT_SUBMITTED",
        "created_by_type": "AGENT",
        "created_by_name": "research-agent",
        "details": {
            "purpose": "Capture route testing guidance.",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "usage_example": "Submit, review, then activate.",
            "required_tools": ["pytest"],
            "risk_level": "MEDIUM",
            "version": "1.0.0",
            "evidence_urls": [],
            "source_summary": None,
            "acquisition_method": "SELF_ACQUISITION",
            "harness": {
                "status": "NEEDS_REVIEW",
                "checks": [
                    {
                        "name": "title_present",
                        "passed": True,
                        "message": "title is present",
                    },
                    {
                        "name": "purpose_present",
                        "passed": True,
                        "message": "purpose is present",
                    },
                    {
                        "name": "content_present",
                        "passed": True,
                        "message": "content is present",
                    },
                    {
                        "name": "evidence_present",
                        "passed": False,
                        "message": "at least one evidence URL is required",
                    },
                ],
            },
            "quality_gate": {
                "status": "NEEDS_REVIEW",
                "checks": [
                    {
                        "name": "title_present",
                        "passed": True,
                        "message": "title is present",
                    },
                    {
                        "name": "content_present",
                        "passed": True,
                        "message": "content is present",
                    },
                    {
                        "name": "dangerous_command_absent",
                        "passed": True,
                        "message": "dangerous shell command marker is absent",
                    },
                    {
                        "name": "secret_redaction",
                        "passed": True,
                        "message": "secret content is redacted or safe",
                    },
                    {
                        "name": "evidence_or_summary_present",
                        "passed": False,
                        "message": "evidence URL or source summary is present",
                    },
                ],
            },
        },
        "created_at": "2026-05-12T10:00:00Z",
        "updated_at": "2026-05-12T10:05:00Z",
    }
    assert item_repo.created_payload is not None
    assert item_repo.created_payload["source_type"] == "AGENT_SUBMITTED"
    assert item_repo.created_payload["created_by_type"] == "AGENT"


def test_submit_skill_by_agent_preserves_self_acquisition_evidence_and_harness() -> (
    None
):
    """Agent submissions should preserve evidence and expose harness status."""
    payload = _valid_submit_skill_by_agent_payload()
    payload["evidence_urls"] = ["https://example.com/hermes-skill-research"]
    payload["source_summary"] = "Hermes researched the missing capability directly."

    status_code, body = _post_submit_skill_by_agent(payload)

    expected_details = {
        "purpose": "Capture route testing guidance.",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "usage_example": "Submit, review, then activate.",
        "required_tools": ["pytest"],
        "risk_level": "MEDIUM",
        "version": "1.0.0",
        "evidence_urls": ["https://example.com/hermes-skill-research"],
        "source_summary": "Hermes researched the missing capability directly.",
        "acquisition_method": "SELF_ACQUISITION",
        "harness": {
            "status": "PASSED",
            "checks": [
                {
                    "name": "title_present",
                    "passed": True,
                    "message": "title is present",
                },
                {
                    "name": "purpose_present",
                    "passed": True,
                    "message": "purpose is present",
                },
                {
                    "name": "content_present",
                    "passed": True,
                    "message": "content is present",
                },
                {
                    "name": "evidence_present",
                    "passed": True,
                    "message": "evidence URL is present",
                },
            ],
        },
        "quality_gate": {
            "status": "PASSED",
            "checks": [
                {
                    "name": "title_present",
                    "passed": True,
                    "message": "title is present",
                },
                {
                    "name": "content_present",
                    "passed": True,
                    "message": "content is present",
                },
                {
                    "name": "dangerous_command_absent",
                    "passed": True,
                    "message": "dangerous shell command marker is absent",
                },
                {
                    "name": "secret_redaction",
                    "passed": True,
                    "message": "secret content is redacted or safe",
                },
                {
                    "name": "evidence_or_summary_present",
                    "passed": True,
                    "message": "evidence URL or source summary is present",
                },
            ],
        },
    }
    assert status_code == 201
    assert body["details"] == expected_details


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("risk_level", "CRITICAL"),
        ("status", "PUBLISHED"),
    ],
)
def test_submit_skill_by_agent_rejects_invalid_enum_strings(
    field: str,
    invalid_value: str,
) -> None:
    """POST /library/skills/submit-by-agent should return 422 for invalid enum strings."""
    payload = _valid_submit_skill_by_agent_payload()
    payload[field] = invalid_value

    status_code, body = _post_submit_skill_by_agent(payload)

    assert status_code == 422
    assert any(error["loc"] == ["body", field] for error in body["detail"])
