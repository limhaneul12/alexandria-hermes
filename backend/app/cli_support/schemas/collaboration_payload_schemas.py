"""CLI-only collaboration request payload schemas."""

from __future__ import annotations

from app.shared.schemas.common_schemas import StrictSchemaModel


class LibrarianAskBody(StrictSchemaModel):
    """Backend ask-librarian request body emitted by CLI adapters."""

    prompt: str
    agent_name: str
    delegate_to_librarian: bool
    provider_id: str | None = None
    librarian_profile_id: str | None = None
    librarian_model: str | None = None
    librarian_role_prompt: str | None = None
    max_librarian_agents: int | None = None
    routing_specialties: list[str] | None = None
    project: str | None = None
    task_summary: str | None = None


class LibrarianProfilePatchBody(StrictSchemaModel):
    """Backend librarian-profile patch body emitted by CLI adapters."""

    name: str | None = None
    librarian_role: str | None = None
    preferred_librarian_provider: str | None = None
    preferred_librarian_model: str | None = None
    max_librarian_agents: int | None = None
    librarian_routing_priority: int | None = None
    librarian_enabled: bool | None = None
    description: str | None = None
    librarian_role_prompt: str | None = None
    capabilities: list[str] | None = None
    librarian_specialties: list[str] | None = None
