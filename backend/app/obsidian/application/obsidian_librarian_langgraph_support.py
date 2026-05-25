"""Support contracts and payload helpers for Obsidian LangGraph workflows."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TypedDict, cast

from app.librarian.domain.contracts.hermes_collaboration_contracts import (
    HermesLibrarianAskCommand,
)
from app.librarian.domain.entities.source_ref import SourceRef, SourceRefType
from app.librarian.domain.types.hermes_collaboration_payload_types import (
    HermesLibrarianAskPayload,
)
from app.obsidian.application.obsidian_graph_relations import source_refs_from_json
from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianLibrarianAsk,
    ObsidianSaveNote,
)
from app.obsidian.domain.entities.obsidian_note import ObsidianLibrarianWorkflow
from app.obsidian.domain.event_enum.obsidian_enums import (
    AlexandriaNoteType,
    ObsidianLibrarianWorkflowStatus,
)
from app.shared.types.extra_types import JSONObject, JSONValue
from langgraph.types import Interrupt


class ObsidianLibrarianDelegateService(ABC):
    """Narrow boundary for GPT/OAuth-backed librarian delegation."""

    @abstractmethod
    async def ask_librarian(
        self,
        command: HermesLibrarianAskCommand,
    ) -> HermesLibrarianAskPayload:
        """Ask the configured Hermes librarian delegate service.

        Args:
            command: Provider/profile-aware librarian command.

        Returns:
            Provider-backed librarian result payload.
        """


class ObsidianLibrarianGraphState(TypedDict, total=False):
    """Serializable LangGraph state for an Obsidian librarian workflow."""

    thread_id: str
    query: str
    active_note_path: str | None
    selection: str | None
    project: str | None
    preferred_alexandria_types: list[str]
    delegate_requested: bool
    provider_id: str | None
    profile_id: str | None
    response: JSONObject
    pending_actions: list[JSONObject]
    approved_actions: list[str]
    completed_actions: list[str]
    transcript_path: str | None
    workflow_status: str
    langgraph_interrupts: list[JSONObject]
    langgraph_checkpoint_path: str
    delegate_payload: JSONObject | None


class ObsidianLibrarianGraphResult(TypedDict, total=False):
    """Result returned by the LangGraph executor boundary."""

    state: JSONObject
    status: str


def _initial_graph_state(
    *,
    thread_id: str,
    ask: ObsidianLibrarianAsk,
    checkpoint_path: str,
) -> ObsidianLibrarianGraphState:
    """Build the first serializable LangGraph state."""
    return {
        "thread_id": thread_id,
        "query": ask.query,
        "active_note_path": ask.active_note_path,
        "selection": ask.selection,
        "project": ask.project,
        "preferred_alexandria_types": [
            note_type.value for note_type in ask.preferred_alexandria_types
        ],
        "delegate_requested": ask.delegate_to_librarian,
        "provider_id": ask.provider_id,
        "profile_id": ask.profile_id,
        "approved_actions": [],
        "completed_actions": [],
        "transcript_path": None,
        "workflow_status": "created",
        "langgraph_checkpoint_path": checkpoint_path,
        "delegate_payload": None,
    }


def _result_from_graph_output(
    output: ObsidianLibrarianGraphState,
) -> ObsidianLibrarianGraphResult:
    """Convert raw LangGraph output into the service boundary result."""
    state = _json_state(output)
    interrupts = _interrupts_from_output(output)
    if interrupts:
        state["langgraph_interrupts"] = interrupts
        state["workflow_status"] = "waiting_for_approval"
        return {"state": state, "status": "waiting_for_approval"}
    status = _state_optional_string(output, "workflow_status") or "completed"
    return {"state": state, "status": status}


def _json_state(output: ObsidianLibrarianGraphState) -> JSONObject:
    """Drop LangGraph runtime-only keys and return a JSON-compatible state."""
    state: JSONObject = {}
    for key, value in output.items():
        if key == "__interrupt__":
            continue
        state[key] = cast(JSONValue, value)
    return state


def _interrupts_from_output(output: ObsidianLibrarianGraphState) -> list[JSONObject]:
    """Extract human-in-the-loop interrupt payloads from LangGraph output."""
    value = output.get("__interrupt__")
    if not isinstance(value, list):
        return []
    return [
        {"id": item.id, "value": cast(JSONValue, item.value)}
        for item in value
        if isinstance(item, Interrupt)
    ]


def _pending_actions_from_state(
    state: ObsidianLibrarianGraphState,
) -> list[JSONObject]:
    """Plan workflow actions that require explicit user approval."""
    actions: list[JSONObject] = [
        _action("save_transcript", "Save transcript", "save_transcript"),
        _action("create_context_note", "Create context note", "create_context"),
        _action("create_skill_draft", "Create skill draft", "create_skill"),
    ]
    if _state_optional_string(state, "active_note_path") is not None:
        actions.insert(1, _action("add_graph_links", "Add graph links", "graph_links"))
    if bool(state.get("delegate_requested")):
        actions.append(
            _action("ask_oauth_librarian", "Ask GPT OAuth librarian", "delegate")
        )
    return actions


def _interrupt_payload(state: ObsidianLibrarianGraphState) -> JSONObject:
    """Build the approval payload emitted by the interrupt node."""
    return {
        "thread_id": _state_string(state, "thread_id"),
        "response": _state_object(state, "response"),
        "pending_actions": _state_json_object_list(state, "pending_actions"),
        "approval_contract": "Command(resume={'approved_actions': [...]})",
    }


def _approved_actions(value: JSONValue) -> list[str]:
    """Normalize approved action ids supplied to LangGraph resume."""
    if not isinstance(value, dict):
        return []
    raw_actions = value.get("approved_actions")
    if not isinstance(raw_actions, list):
        return []
    return sorted(item for item in raw_actions if isinstance(item, str))


def _pending_action_ids(state: ObsidianLibrarianGraphState) -> set[str]:
    """Return the pending action id set from state."""
    ids: set[str] = set()
    for item in _state_json_object_list(state, "pending_actions"):
        action_id = item.get("id")
        if isinstance(action_id, str):
            ids.add(action_id)
    return ids


def _ask_from_state(state: ObsidianLibrarianGraphState) -> ObsidianLibrarianAsk:
    """Rebuild an ask command from serializable LangGraph state."""
    return ObsidianLibrarianAsk(
        query=_state_string(state, "query"),
        active_note_path=_state_optional_string(state, "active_note_path"),
        selection=_state_optional_string(state, "selection"),
        project=_state_optional_string(state, "project"),
        preferred_alexandria_types=[],
        delegate_to_librarian=bool(state.get("delegate_requested")),
        provider_id=_state_optional_string(state, "provider_id"),
        profile_id=_state_optional_string(state, "profile_id"),
    )


def _workflow_snapshot_from_state(
    state: ObsidianLibrarianGraphState,
) -> ObsidianLibrarianWorkflow:
    """Build a transient workflow entity for post-approval action helpers."""
    current = datetime.now(UTC)
    return ObsidianLibrarianWorkflow(
        thread_id=_state_string(state, "thread_id"),
        status=ObsidianLibrarianWorkflowStatus.WAITING_FOR_APPROVAL,
        query=_state_string(state, "query"),
        active_note_path=_state_optional_string(state, "active_note_path"),
        project=_state_optional_string(state, "project"),
        provider_id=_state_optional_string(state, "provider_id"),
        profile_id=_state_optional_string(state, "profile_id"),
        delegate_requested=bool(state.get("delegate_requested")),
        state=_json_state(state),
        created_at=current,
        updated_at=current,
    )


def _save_note_command(
    *,
    workflow: ObsidianLibrarianWorkflow,
    title: str,
    body: str,
    alexandria_type: AlexandriaNoteType,
    note_id: str | None,
    relation_field: str,
    refs: list[JSONObject],
) -> ObsidianSaveNote:
    """Build an Obsidian save command for approved workflow writes."""
    return ObsidianSaveNote(
        title=title,
        body=body,
        alexandria_type=alexandria_type,
        note_id=note_id,
        tags=["alexandria", "librarian", "workflow"],
        project=workflow.project,
        source="obsidian-librarian-langgraph",
        frontmatter={
            "workflow_thread_id": workflow.thread_id,
            "workflow_engine": "langgraph",
            "active_note_path": workflow.active_note_path,
            relation_field: refs,
        },
    )


def _transcript_body(workflow: ObsidianLibrarianWorkflow, response: JSONObject) -> str:
    """Render a transcript note body from a workflow response."""
    return f"""# Librarian Workflow

## Engine
LangGraph

## User
{workflow.query}

## Librarian
{response.get("answer_markdown") or ""}
"""


def _delegate_prompt(
    workflow: ObsidianLibrarianWorkflow,
    response: JSONObject,
) -> str:
    """Render the prompt sent to the approved GPT/OAuth librarian delegate."""
    return "\n\n".join(
        [
            "Review this Obsidian-grounded librarian answer.",
            f"Question: {workflow.query}",
            f"Active note: {workflow.active_note_path or 'none'}",
            "Return concise GPT OAuth librarian guidance with risks, missing sources, and graph/memory follow-up actions.",
            str(response.get("answer_markdown") or ""),
        ]
    )


def _delegate_brief(
    workflow: ObsidianLibrarianWorkflow,
    response: JSONObject,
) -> str:
    """Render a structured delegate brief for provider-backed librarian calls."""
    source_paths = [
        str(ref.get("path"))
        for ref in source_refs_from_json(response.get("source_refs"))
        if isinstance(ref.get("path"), str)
    ]
    return "\n".join(
        [
            "# Obsidian Librarian Delegate Brief",
            f"- query: {workflow.query}",
            f"- project: {workflow.project or 'default'}",
            f"- active_note_path: {workflow.active_note_path or 'none'}",
            f"- source_paths: {', '.join(source_paths) if source_paths else 'none'}",
            "",
            str(response.get("answer_markdown") or ""),
        ]
    )


def _source_refs(response: JSONObject) -> tuple[SourceRef, ...]:
    """Convert Obsidian source refs into Hermes librarian source refs."""
    refs: list[SourceRef] = []
    for item in source_refs_from_json(response.get("source_refs")):
        note_id = item.get("id")
        path = item.get("path")
        title = item.get("title")
        if not isinstance(note_id, str) or not isinstance(path, str):
            continue
        refs.append(
            SourceRef(
                source_type=SourceRefType.CONTEXT,
                source_id=note_id,
                title=title if isinstance(title, str) and title else path,
                detail_path=f"/obsidian/notes/{note_id}",
                preview=path,
            )
        )
    return tuple(refs)


def _delegate_status(
    payload: JSONObject | None,
    response: JSONObject,
) -> str:
    """Normalize delegate execution status for the workflow state."""
    if payload is None:
        status_value = response.get("delegate_status")
        return status_value if isinstance(status_value, str) else "local_only"
    status_value = payload.get("status")
    if isinstance(status_value, str):
        return status_value
    return "delegate_status_unknown"


def _delegate_unavailable_payload(
    workflow: ObsidianLibrarianWorkflow,
    reason: str,
) -> JSONObject:
    """Return a guidance-only delegate result when requested OAuth setup is missing."""
    return {
        "job_id": f"{workflow.thread_id}:delegate-unavailable",
        "status": "GUIDANCE_ONLY",
        "decision": "SUGGEST_HERMES_RESEARCH",
        "librarian_available": False,
        "self_acquisition_allowed": True,
        "recommendation": reason,
        "provider_id": workflow.provider_id,
        "candidate_id": None,
        "librarian_profile_id": workflow.profile_id,
        "librarian_model": None,
        "librarian_role_prompt": None,
        "max_librarian_agents": 1,
        "route_preview": ["GPT OAuth librarian unavailable"],
        "selected_profiles": [],
        "matched_specialties": [],
        "quality_review_added": False,
        "routing_reason": reason,
        "delegates": [],
    }


def _append_delegate_summary(
    response: JSONObject,
    delegate_payload: JSONObject | None,
) -> None:
    """Append delegate summaries to the local answer markdown in-place."""
    if delegate_payload is None:
        return
    summaries: list[str] = []
    delegates = delegate_payload.get("delegates")
    if isinstance(delegates, list):
        for item in delegates:
            if not isinstance(item, dict):
                continue
            summary = item.get("summary")
            if isinstance(summary, str) and summary.strip():
                summaries.append(summary.strip())
    if not summaries:
        recommendation = delegate_payload.get("recommendation")
        if isinstance(recommendation, str) and recommendation.strip():
            summaries.append(recommendation.strip())
    if not summaries:
        return
    answer = str(response.get("answer_markdown") or "")
    response["answer_markdown"] = "\n\n".join(
        [
            answer,
            "## GPT OAuth Librarian",
            "\n\n".join(summaries),
        ]
    )


def _state_string(state: ObsidianLibrarianGraphState, key: str) -> str:
    """Read a string state field or return an empty string."""
    value = state.get(key)
    return value if isinstance(value, str) else ""


def _state_optional_string(
    state: ObsidianLibrarianGraphState,
    key: str,
) -> str | None:
    """Read a non-empty optional string state field."""
    value = state.get(key)
    return value if isinstance(value, str) and value else None


def _state_object(state: ObsidianLibrarianGraphState, key: str) -> JSONObject:
    """Read a JSON object state field."""
    value = state.get(key)
    return dict(value) if isinstance(value, dict) else {}


def _state_list(state: ObsidianLibrarianGraphState, key: str) -> list[JSONValue]:
    """Read a JSON list state field."""
    value = state.get(key)
    return list(value) if isinstance(value, list) else []


def _state_string_list(
    state: ObsidianLibrarianGraphState,
    key: str,
) -> list[str]:
    """Read a string list state field."""
    return [item for item in _state_list(state, key) if isinstance(item, str)]


def _state_json_object_list(
    state: ObsidianLibrarianGraphState,
    key: str,
) -> list[JSONObject]:
    """Read a JSON object list state field."""
    return [dict(item) for item in _state_list(state, key) if isinstance(item, dict)]


def _action(action_id: str, label: str, action_type: str) -> JSONObject:
    return {
        "id": action_id,
        "label": label,
        "type": action_type,
        "requires_approval": True,
    }
