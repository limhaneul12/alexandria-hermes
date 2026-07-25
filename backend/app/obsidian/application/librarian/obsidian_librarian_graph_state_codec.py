"""Serializable state construction, decoding, and workflow snapshots."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from app.obsidian.application.librarian.obsidian_librarian_graph_contracts import (
    ObsidianLibrarianGraphResult,
    ObsidianLibrarianGraphState,
)
from app.obsidian.application.librarian.obsidian_librarian_state_access import (
    state_int as _state_int,
    state_json_object_list as _state_json_object_list,
    state_note_types as _state_note_types,
    state_optional_string as _state_optional_string,
    state_string as _state_string,
)
from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianLibrarianAsk,
)
from app.obsidian.domain.entities.obsidian_note import ObsidianLibrarianWorkflow
from app.obsidian.domain.event_enum.obsidian_enums import (
    ObsidianLibrarianWorkflowStatus,
)
from app.shared.types.extra_types import JSONObject, JSONValue
from langgraph.types import Interrupt


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
        "max_source_refs": ask.max_source_refs,
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
        preferred_alexandria_types=tuple(_state_note_types(state)),
        max_source_refs=_state_int(state, "max_source_refs", 12),
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
