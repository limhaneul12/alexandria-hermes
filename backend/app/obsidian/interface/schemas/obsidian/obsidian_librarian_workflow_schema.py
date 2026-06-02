"""HTTP schemas for Obsidian librarian ask/workflow operations."""

from __future__ import annotations

from app.obsidian.domain.contracts.obsidian_contracts import ObsidianLibrarianAsk
from app.obsidian.domain.entities.obsidian_note import ObsidianLibrarianWorkflow
from app.obsidian.domain.event_enum.obsidian_enums import (
    AlexandriaNoteType,
    ObsidianLibrarianWorkflowStatus,
)
from app.obsidian.interface.schemas.obsidian.obsidian_librarian_type_aliases import (
    preferred_note_type_input,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.types.extra_types import JSONObject, JSONValue
from pydantic import Field, field_validator


class ObsidianLibrarianAskRequest(StrictSchemaModel):
    """Ask the Obsidian-aware Alexandria librarian."""

    query: str = Field(min_length=1)
    active_note_path: str | None = None
    selection: str | None = None
    project: str | None = None
    preferred_alexandria_types: list[AlexandriaNoteType] = Field(default_factory=list)
    max_source_refs: int = Field(default=12, ge=1, le=50)
    save_transcript: bool = False
    delegate_to_librarian: bool = False
    provider_id: str | None = None
    profile_id: str | None = None

    @field_validator("preferred_alexandria_types", mode="before")
    @classmethod
    def normalize_preferred_alexandria_types(cls, value: JSONValue) -> JSONValue:
        """Normalize agent-facing note type aliases before enum validation.

        MCP callers provide this field as free strings. The Obsidian shelf named
        "Indexes" stores notes as Alexandria context notes, so accepting
        "index" avoids a brittle 422 for otherwise valid librarian requests.

        Args:
            value: Raw Pydantic input value before enum validation.

        Returns:
            Normalized value for downstream enum validation.
        """
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        return [preferred_note_type_input(item) for item in value]

    def to_command(self) -> ObsidianLibrarianAsk:
        """Convert request into application command.

        Returns:
            Application librarian ask command.
        """
        return ObsidianLibrarianAsk(
            query=self.query,
            active_note_path=self.active_note_path,
            selection=self.selection,
            project=self.project,
            preferred_alexandria_types=[
                _note_type(note_type) for note_type in self.preferred_alexandria_types
            ],
            max_source_refs=self.max_source_refs,
            save_transcript=self.save_transcript,
            delegate_to_librarian=self.delegate_to_librarian,
            provider_id=self.provider_id,
            profile_id=self.profile_id,
        )


class ObsidianSourceRefResponse(StrictSchemaModel):
    """Source reference returned from an Obsidian librarian answer."""

    id: str
    alexandria_type: str
    path: str
    title: str
    wikilink: str


class ObsidianLibrarianAskResponse(StrictSchemaModel):
    """Response from the Obsidian-aware librarian adapter."""

    answer_markdown: str
    source_refs: list[ObsidianSourceRefResponse]
    input_context: JSONObject
    context_status: str
    action_preview: list[str]
    conversation_id: str
    transcript_path: str | None
    delegate_status: str = "local_only"
    provider_id: str | None = None
    profile_id: str | None = None


class ObsidianLibrarianWorkflowResumeRequest(StrictSchemaModel):
    """Approved actions for resuming a librarian workflow."""

    approved_actions: list[str] = Field(default_factory=list)


class ObsidianLibrarianWorkflowResponse(StrictSchemaModel):
    """Resumable librarian workflow response."""

    thread_id: str
    status: ObsidianLibrarianWorkflowStatus
    query: str
    active_note_path: str | None
    project: str | None
    provider_id: str | None
    profile_id: str | None
    delegate_requested: bool
    response: JSONObject
    pending_actions: list[JSONObject]
    approved_actions: list[str]
    completed_actions: list[str]
    transcript_path: str | None

    @classmethod
    def from_entity(
        cls, workflow: ObsidianLibrarianWorkflow
    ) -> ObsidianLibrarianWorkflowResponse:
        """Create schema from workflow checkpoint.

        Args:
            workflow: Persisted workflow checkpoint.

        Returns:
            HTTP workflow schema.
        """
        state = workflow.state
        return cls(
            thread_id=workflow.thread_id,
            status=workflow.status,
            query=workflow.query,
            active_note_path=workflow.active_note_path,
            project=workflow.project,
            provider_id=workflow.provider_id,
            profile_id=workflow.profile_id,
            delegate_requested=workflow.delegate_requested,
            response=_object_list_safe(state, "response"),
            pending_actions=_json_object_list(state, "pending_actions"),
            approved_actions=_string_list(state, "approved_actions"),
            completed_actions=_string_list(state, "completed_actions"),
            transcript_path=_optional_string(state.get("transcript_path")),
        )


def _object_list_safe(state: JSONObject, key: str) -> JSONObject:
    value = state.get(key)
    return dict(value) if isinstance(value, dict) else {}


def _json_object_list(state: JSONObject, key: str) -> list[JSONObject]:
    value = state.get(key)
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _string_list(state: JSONObject, key: str) -> list[str]:
    value = state.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _optional_string(value: JSONValue | None) -> str | None:
    return value if isinstance(value, str) and value else None


def _note_type(value: AlexandriaNoteType | str) -> AlexandriaNoteType:
    if isinstance(value, AlexandriaNoteType):
        return value
    return AlexandriaNoteType(value)
