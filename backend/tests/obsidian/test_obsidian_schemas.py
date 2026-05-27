"""Obsidian HTTP schema conversion tests."""

from __future__ import annotations

from app.obsidian.domain.event_enum.obsidian_enums import AlexandriaNoteType
from app.obsidian.interface.schemas.obsidian.obsidian_schema import (
    ObsidianLibrarianAskRequest,
    ObsidianSaveNoteRequest,
    ObsidianSearchRequest,
)


def test_obsidian_request_schemas_restore_enum_contracts() -> None:
    """Pydantic enum-value schemas should still emit domain enum contracts."""
    search = ObsidianSearchRequest(query="cache", alexandria_type="context")
    save = ObsidianSaveNoteRequest(
        title="Smoke",
        body="body",
        alexandria_type="job_plan",
    )
    ask = ObsidianLibrarianAskRequest(
        query="cache",
        preferred_alexandria_types=["context", "skill"],
    )

    assert search.to_query().alexandria_type is AlexandriaNoteType.CONTEXT
    assert ObsidianSearchRequest(query="cache").to_query().alexandria_type is None
    assert save.to_command().alexandria_type is AlexandriaNoteType.JOB_PLAN
    assert ask.to_command().preferred_alexandria_types == [
        AlexandriaNoteType.CONTEXT,
        AlexandriaNoteType.SKILL,
    ]


def test_obsidian_librarian_request_accepts_agent_type_aliases() -> None:
    """Agent-facing librarian calls should accept common shelf/type aliases."""
    ask = ObsidianLibrarianAskRequest(
        query="compact the index",
        preferred_alexandria_types=["index", "memory"],
    )

    assert ask.to_command().preferred_alexandria_types == [
        AlexandriaNoteType.CONTEXT,
        AlexandriaNoteType.MEMORY_COMPACT,
    ]
