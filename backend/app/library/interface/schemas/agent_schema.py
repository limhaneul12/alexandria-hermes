"""Agent profile request and response schemas."""

from __future__ import annotations

from datetime import datetime

from app.library.interface.schemas._types import StrictSchema
from pydantic import ConfigDict


class AgentCreateRequest(StrictSchema):
    """Payload for registering an agent profile."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "name": "research-agent",
                    "provider": "OPENAI",
                    "description": "Finds reusable backend implementation guidance.",
                    "capabilities": ["search", "summarize"],
                    "preferred_librarian_provider": 1,
                }
            ]
        },
    )

    name: str
    provider: str
    description: str | None = None
    capabilities: list[str]
    preferred_librarian_provider: int | None = None


class AgentPatchRequest(StrictSchema):
    """Payload for updating fields on an existing agent."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "description": "Focuses on FastAPI library guidance.",
                    "capabilities": ["search", "recommend"],
                    "preferred_librarian_provider": 2,
                }
            ]
        }
    )

    description: str | None = None
    capabilities: list[str] | None = None
    preferred_librarian_provider: int | None = None


class AgentResponse(StrictSchema):
    """Agent profile response model."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "name": "research-agent",
                    "provider": "OPENAI",
                    "description": "Finds reusable backend implementation guidance.",
                    "capabilities": ["search", "summarize"],
                    "preferred_librarian_provider": 1,
                    "created_at": "2026-05-12T10:00:00Z",
                    "updated_at": "2026-05-12T10:05:00Z",
                }
            ]
        }
    )

    id: int
    name: str
    provider: str
    description: str | None
    capabilities: list[str]
    preferred_librarian_provider: int | None
    created_at: datetime
    updated_at: datetime
