"""Resumable Obsidian librarian workflow application service."""

from __future__ import annotations

from datetime import UTC, datetime

from app.obsidian.application.obsidian_graph_relations import source_refs_from_json
from app.obsidian.application.obsidian_note_templates import conversation_id
from app.obsidian.application.obsidian_service import ObsidianService
from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianLibrarianAsk,
    ObsidianLibrarianWorkflowResume,
    ObsidianSaveNote,
)
from app.obsidian.domain.entities.obsidian_note import (
    ObsidianLibrarianWorkflow,
    ObsidianNote,
)
from app.obsidian.domain.event_enum.obsidian_enums import (
    AlexandriaNoteType,
    ObsidianLibrarianWorkflowStatus,
)
from app.obsidian.domain.repositories.obsidian_repository import (
    IObsidianWorkflowRepository,
)
from app.shared.exceptions import ObsidianNotFoundError, ObsidianValidationError
from app.shared.types.extra_types import JSONObject, JSONValue


class ObsidianLibrarianWorkflowService:
    """Run a local LangGraph-style librarian workflow with approval checkpoints."""

    def __init__(
        self,
        *,
        workflow_repository: IObsidianWorkflowRepository,
        obsidian_service: ObsidianService,
    ) -> None:
        self._workflow_repository = workflow_repository
        self._obsidian_service = obsidian_service

    async def start_workflow(
        self,
        ask: ObsidianLibrarianAsk,
    ) -> ObsidianLibrarianWorkflow:
        """Start and pause a librarian workflow for human approval.

        Args:
            ask: Obsidian librarian ask payload.

        Returns:
            Persisted waiting workflow checkpoint.
        """
        response = await self._obsidian_service.ask_librarian(
            ObsidianLibrarianAsk(
                query=ask.query,
                active_note_path=ask.active_note_path,
                selection=ask.selection,
                project=ask.project,
                preferred_alexandria_types=ask.preferred_alexandria_types,
                save_transcript=False,
                delegate_to_librarian=ask.delegate_to_librarian,
                provider_id=ask.provider_id,
                profile_id=ask.profile_id,
            )
        )
        thread_id = str(response.get("conversation_id") or conversation_id())
        state = _initial_state(thread_id, ask, response)
        workflow = _workflow_from_state(
            thread_id=thread_id,
            ask=ask,
            state=state,
            status=ObsidianLibrarianWorkflowStatus.WAITING_FOR_APPROVAL,
            created_at=datetime.now(UTC),
        )
        await self._workflow_repository.upsert_workflow(workflow)
        return workflow

    async def get_workflow(self, thread_id: str) -> ObsidianLibrarianWorkflow:
        """Read one workflow checkpoint.

        Args:
            thread_id: Workflow thread id.

        Returns:
            Persisted workflow checkpoint.
        """
        workflow = await self._workflow_repository.get_workflow(thread_id)
        if workflow is None:
            raise ObsidianNotFoundError(f"Obsidian workflow not found: {thread_id}")
        return workflow

    async def resume_workflow(
        self,
        command: ObsidianLibrarianWorkflowResume,
    ) -> ObsidianLibrarianWorkflow:
        """Apply approved actions and complete the workflow.

        Args:
            command: Resume command with approved action ids.

        Returns:
            Completed workflow checkpoint.
        """
        workflow = await self.get_workflow(command.thread_id)
        if workflow.status == ObsidianLibrarianWorkflowStatus.CANCELLED:
            raise ObsidianValidationError("workflow is cancelled")
        if workflow.status != ObsidianLibrarianWorkflowStatus.WAITING_FOR_APPROVAL:
            raise ObsidianValidationError("workflow is not waiting for approval")
        state = dict(workflow.state)
        response = _object_state(state, "response")
        completed_actions = list(_list_state(state, "completed_actions"))
        transcript_path = _string_state(state, "transcript_path")
        approved = set(command.approved_actions)
        unknown_actions = approved.difference(_pending_action_ids(state))
        if unknown_actions:
            unknown = ", ".join(sorted(unknown_actions))
            raise ObsidianValidationError(f"unknown workflow action: {unknown}")
        if "save_transcript" in approved and transcript_path is None:
            note = await self._save_transcript(workflow, response)
            transcript_path = note.relative_path
            response["transcript_path"] = transcript_path
            completed_actions.append("save_transcript")
        if "create_context_note" in approved:
            note = await self._create_answer_note(workflow, response, "context")
            completed_actions.append(f"create_context_note:{note.relative_path}")
        if "create_skill_draft" in approved:
            note = await self._create_answer_note(workflow, response, "skill")
            completed_actions.append(f"create_skill_draft:{note.relative_path}")
        if "add_graph_links" in approved:
            completed_actions.append("add_graph_links:pending-plugin-apply")
        if "ask_oauth_librarian" in approved:
            status_value = response.get("delegate_status")
            delegate_status = (
                status_value if isinstance(status_value, str) else "local_only"
            )
            completed_actions.append(f"ask_oauth_librarian:{delegate_status}")
        state.update(
            {
                "approved_actions": sorted(approved),
                "completed_actions": completed_actions,
                "response": response,
                "transcript_path": transcript_path,
            }
        )
        updated = _workflow_from_state(
            thread_id=workflow.thread_id,
            ask=_ask_from_workflow(workflow),
            state=state,
            status=ObsidianLibrarianWorkflowStatus.COMPLETED,
            created_at=workflow.created_at,
        )
        await self._workflow_repository.upsert_workflow(updated)
        return updated

    async def cancel_workflow(self, thread_id: str) -> ObsidianLibrarianWorkflow:
        """Cancel a waiting workflow without writing Obsidian notes.

        Args:
            thread_id: Workflow thread id.

        Returns:
            Cancelled workflow checkpoint.
        """
        workflow = await self.get_workflow(thread_id)
        updated = ObsidianLibrarianWorkflow(
            thread_id=workflow.thread_id,
            status=ObsidianLibrarianWorkflowStatus.CANCELLED,
            query=workflow.query,
            active_note_path=workflow.active_note_path,
            project=workflow.project,
            provider_id=workflow.provider_id,
            profile_id=workflow.profile_id,
            delegate_requested=workflow.delegate_requested,
            state=workflow.state,
            created_at=workflow.created_at,
            updated_at=datetime.now(UTC),
        )
        await self._workflow_repository.upsert_workflow(updated)
        return updated

    async def _save_transcript(
        self,
        workflow: ObsidianLibrarianWorkflow,
        response: JSONObject,
    ) -> ObsidianNote:
        body = _transcript_body(workflow, response)
        refs = source_refs_from_json(response.get("source_refs"))
        return await self._obsidian_service.save_note(
            _save_note_command(
                workflow=workflow,
                title=f"Librarian Chat {workflow.thread_id}",
                body=body,
                alexandria_type=AlexandriaNoteType.LIBRARIAN_CHAT,
                note_id=workflow.thread_id,
                relation_field="source_refs",
                refs=refs,
            )
        )

    async def _create_answer_note(
        self,
        workflow: ObsidianLibrarianWorkflow,
        response: JSONObject,
        note_kind: str,
    ) -> ObsidianNote:
        alexandria_type = (
            AlexandriaNoteType.SKILL
            if note_kind == "skill"
            else AlexandriaNoteType.CONTEXT
        )
        title = (
            "Alexandria Skill Draft"
            if note_kind == "skill"
            else "Alexandria Context Note"
        )
        return await self._obsidian_service.save_note(
            _save_note_command(
                workflow=workflow,
                title=title,
                body=str(response.get("answer_markdown") or ""),
                alexandria_type=alexandria_type,
                note_id=None,
                relation_field="derived_from",
                refs=[
                    {
                        "id": workflow.thread_id,
                        "path": str(response.get("transcript_path") or ""),
                        "relation": "derived_from",
                    }
                ],
            )
        )


def _initial_state(
    thread_id: str,
    ask: ObsidianLibrarianAsk,
    response: JSONObject,
) -> JSONObject:
    actions: list[JSONObject] = [
        _action("save_transcript", "Save transcript", "save_transcript"),
        _action("create_context_note", "Create context note", "create_context"),
        _action("create_skill_draft", "Create skill draft", "create_skill"),
    ]
    if ask.active_note_path:
        actions.insert(1, _action("add_graph_links", "Add graph links", "graph_links"))
    if ask.delegate_to_librarian:
        actions.append(
            _action("ask_oauth_librarian", "Ask OAuth librarian", "delegate")
        )
    return {
        "thread_id": thread_id,
        "response": response,
        "pending_actions": actions,
        "approved_actions": [],
        "completed_actions": [],
        "transcript_path": None,
    }


def _action(action_id: str, label: str, action_type: str) -> JSONObject:
    return {
        "id": action_id,
        "label": label,
        "type": action_type,
        "requires_approval": True,
    }


def _workflow_from_state(
    *,
    thread_id: str,
    ask: ObsidianLibrarianAsk,
    state: JSONObject,
    status: ObsidianLibrarianWorkflowStatus,
    created_at: datetime,
) -> ObsidianLibrarianWorkflow:
    return ObsidianLibrarianWorkflow(
        thread_id=thread_id,
        status=status,
        query=ask.query,
        active_note_path=ask.active_note_path,
        project=ask.project,
        provider_id=ask.provider_id,
        profile_id=ask.profile_id,
        delegate_requested=ask.delegate_to_librarian,
        state=state,
        created_at=created_at,
        updated_at=datetime.now(UTC),
    )


def _ask_from_workflow(workflow: ObsidianLibrarianWorkflow) -> ObsidianLibrarianAsk:
    return ObsidianLibrarianAsk(
        query=workflow.query,
        active_note_path=workflow.active_note_path,
        project=workflow.project,
        delegate_to_librarian=workflow.delegate_requested,
        provider_id=workflow.provider_id,
        profile_id=workflow.profile_id,
    )


def _object_state(state: JSONObject, key: str) -> JSONObject:
    value = state.get(key)
    return dict(value) if isinstance(value, dict) else {}


def _list_state(state: JSONObject, key: str) -> list[JSONValue]:
    value = state.get(key)
    return list(value) if isinstance(value, list) else []


def _pending_action_ids(state: JSONObject) -> set[str]:
    ids: set[str] = set()
    for item in _list_state(state, "pending_actions"):
        if isinstance(item, dict):
            action_id = item.get("id")
            if isinstance(action_id, str):
                ids.add(action_id)
    return ids


def _string_state(state: JSONObject, key: str) -> str | None:
    value = state.get(key)
    return value if isinstance(value, str) and value else None


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
    return ObsidianSaveNote(
        title=title,
        body=body,
        alexandria_type=alexandria_type,
        note_id=note_id,
        tags=["alexandria", "librarian", "workflow"],
        project=workflow.project,
        source="obsidian-librarian-workflow",
        frontmatter={
            "workflow_thread_id": workflow.thread_id,
            "active_note_path": workflow.active_note_path,
            relation_field: refs,
        },
    )


def _transcript_body(workflow: ObsidianLibrarianWorkflow, response: JSONObject) -> str:
    return f"""# Librarian Workflow

## User
{workflow.query}

## Librarian
{response.get("answer_markdown") or ""}
"""
