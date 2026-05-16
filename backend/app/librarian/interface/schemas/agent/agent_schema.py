"""Agent profile request and response schemas."""

from __future__ import annotations

from datetime import datetime

from app.librarian.domain.event_enum.collaboration_enums import LibrarianProfileRole
from app.shared.schemas.common_schemas import StrictRootSchemaModel, StrictSchemaModel
from pydantic import ConfigDict, Field, field_validator, model_validator


class AgentCreateRequest(StrictSchemaModel):
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
                    "preferred_librarian_provider": "00000000-0000-4000-8000-000000000777",
                    "preferred_librarian_model": "gpt-5.5",
                    "max_librarian_agents": 3,
                    "librarian_role_prompt": "Act as a codebase librarian.",
                    "librarian_role": "SPECIALIST",
                    "librarian_specialties": ["python", "fastapi"],
                    "librarian_routing_priority": 20,
                    "librarian_enabled": True,
                }
            ]
        },
    )

    name: str
    provider: str
    description: str | None = None
    capabilities: list[str]
    preferred_librarian_provider: str | None = None
    preferred_librarian_model: str | None = None
    max_librarian_agents: int = Field(default=1, ge=1, le=6)
    librarian_role_prompt: str | None = Field(default=None, max_length=4096)
    librarian_role: LibrarianProfileRole = LibrarianProfileRole.DEFAULT_SEARCH
    librarian_specialties: list[str] = Field(default_factory=list)
    librarian_routing_priority: int = Field(default=100, ge=0)
    librarian_enabled: bool = True

    @field_validator("librarian_role", mode="before")
    @classmethod
    def parse_librarian_role(
        cls, value: LibrarianProfileRole | str
    ) -> LibrarianProfileRole:
        """Parse public JSON role strings.

        Args:
            value: Incoming role enum or public string value.

        Returns:
            LibrarianProfileRole: Parsed role enum.
        """
        if isinstance(value, LibrarianProfileRole):
            return value
        if isinstance(value, str):
            return LibrarianProfileRole(value)
        raise ValueError("librarian_role must be a valid profile role")


class AgentPatchRequest(StrictSchemaModel):
    """Payload for updating fields on an existing agent."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "research-agent",
                    "description": "Focuses on FastAPI library guidance.",
                    "capabilities": ["search", "recommend"],
                    "preferred_librarian_model": "gpt-5.5",
                    "max_librarian_agents": 2,
                    "librarian_role_prompt": "Find project memory and reusable skills.",
                    "librarian_role": "SPECIALIST",
                    "librarian_specialties": ["fastapi", "oauth"],
                    "librarian_routing_priority": 10,
                    "librarian_enabled": True,
                }
            ]
        }
    )

    name: str | None = None
    provider: str | None = None
    description: str | None = None
    capabilities: list[str] | None = None
    preferred_librarian_provider: str | None = None
    preferred_librarian_model: str | None = None
    max_librarian_agents: int | None = Field(default=None, ge=1, le=6)
    librarian_role_prompt: str | None = Field(default=None, max_length=4096)
    librarian_role: LibrarianProfileRole | None = None
    librarian_specialties: list[str] | None = None
    librarian_routing_priority: int | None = Field(default=None, ge=0)
    librarian_enabled: bool | None = None

    @field_validator("librarian_role", mode="before")
    @classmethod
    def parse_librarian_role(
        cls, value: LibrarianProfileRole | str | None
    ) -> LibrarianProfileRole | None:
        """Parse public JSON role strings when provided.

        Args:
            value: Incoming optional role enum or public string value.

        Returns:
            LibrarianProfileRole | None: Parsed role enum, or None when omitted.
        """
        if value is None:
            return None
        if isinstance(value, LibrarianProfileRole):
            return value
        if isinstance(value, str):
            return LibrarianProfileRole(value)
        raise ValueError("librarian_role must be a valid profile role")

    @model_validator(mode="after")
    def require_actionable_patch(self) -> AgentPatchRequest:
        """Reject empty patches and nulls for non-nullable profile fields.

        Returns:
            AgentPatchRequest: Validated patch request.
        """
        fields = self.model_fields_set
        if not fields:
            raise ValueError("At least one agent field is required")
        if "name" in fields and self.name is None:
            raise ValueError("name cannot be null")
        if "provider" in fields and self.provider is None:
            raise ValueError("provider cannot be null")
        if "capabilities" in fields and self.capabilities is None:
            raise ValueError("capabilities cannot be null")
        if "max_librarian_agents" in fields and self.max_librarian_agents is None:
            raise ValueError("max_librarian_agents cannot be null")
        if "librarian_role" in fields and self.librarian_role is None:
            raise ValueError("librarian_role cannot be null")
        if "librarian_specialties" in fields and self.librarian_specialties is None:
            raise ValueError("librarian_specialties cannot be null")
        if (
            "librarian_routing_priority" in fields
            and self.librarian_routing_priority is None
        ):
            raise ValueError("librarian_routing_priority cannot be null")
        if "librarian_enabled" in fields and self.librarian_enabled is None:
            raise ValueError("librarian_enabled cannot be null")
        return self


class AgentResponse(StrictSchemaModel):
    """Agent profile response model."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "00000000-0000-4000-8000-000000000201",
                    "name": "research-agent",
                    "provider": "OPENAI",
                    "description": "Finds reusable backend implementation guidance.",
                    "capabilities": ["search", "summarize"],
                    "preferred_librarian_provider": "00000000-0000-4000-8000-000000000777",
                    "preferred_librarian_model": "gpt-5.5",
                    "max_librarian_agents": 3,
                    "librarian_role_prompt": "Act as a codebase librarian.",
                    "librarian_role": "SPECIALIST",
                    "librarian_specialties": ["python", "fastapi"],
                    "librarian_routing_priority": 20,
                    "librarian_enabled": True,
                    "created_at": "2026-05-12T10:00:00Z",
                    "updated_at": "2026-05-12T10:05:00Z",
                }
            ]
        },
    )

    id: str
    name: str
    provider: str
    description: str | None
    capabilities: list[str]
    preferred_librarian_provider: str | None
    preferred_librarian_model: str | None
    max_librarian_agents: int
    librarian_role_prompt: str | None
    librarian_role: LibrarianProfileRole
    librarian_specialties: list[str]
    librarian_routing_priority: int
    librarian_enabled: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("librarian_role", mode="before")
    @classmethod
    def parse_librarian_role(
        cls, value: LibrarianProfileRole | str
    ) -> LibrarianProfileRole:
        """Parse persisted role values into the public enum.

        Args:
            value: Persisted role enum or string value.

        Returns:
            LibrarianProfileRole: Parsed role enum.
        """
        if isinstance(value, LibrarianProfileRole):
            return value
        if isinstance(value, str):
            return LibrarianProfileRole(value)
        raise ValueError("librarian_role must be a valid profile role")

    @field_validator("librarian_specialties", mode="before")
    @classmethod
    def parse_librarian_specialties(cls, value: list[str] | None) -> list[str]:
        """Normalize legacy null specialties to an empty list.

        Args:
            value: Persisted specialties or legacy null.

        Returns:
            list[str]: Normalized specialties list.
        """
        if value is None:
            return []
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return value
        raise ValueError("librarian_specialties must be a list of strings")


class AgentResponseList(StrictRootSchemaModel[list[AgentResponse]]):
    """Root response schema for agent response arrays."""
