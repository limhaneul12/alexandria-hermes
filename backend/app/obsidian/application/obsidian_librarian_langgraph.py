"""LangGraph executor for resumable Obsidian librarian workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from app.librarian.domain.contracts.hermes_collaboration_contracts import (
    HermesLibrarianAskCommand,
)
from app.obsidian.application.obsidian_graph_relations import source_refs_from_json
from app.obsidian.application.obsidian_librarian_langgraph_support import (
    ObsidianLibrarianDelegateService,
    ObsidianLibrarianGraphResult,
    ObsidianLibrarianGraphState,
    _append_delegate_summary as append_delegate_summary,
    _approved_actions as approved_actions,
    _ask_from_state as ask_from_state,
    _delegate_status as delegate_status,
    _delegate_unavailable_payload as delegate_unavailable_payload,
    _initial_graph_state as initial_graph_state,
    _interrupt_payload as interrupt_payload,
    _pending_action_ids as pending_action_ids,
    _pending_actions_from_state as pending_actions_from_state,
    _result_from_graph_output as result_from_graph_output,
    _save_note_command as save_note_command,
    _source_refs as source_refs,
    _state_object as state_object,
    _state_optional_string as state_optional_string,
    _state_string as state_string,
    _transcript_body as transcript_body,
    _workflow_snapshot_from_state as workflow_snapshot_from_state,
)
from app.obsidian.application.obsidian_librarian_state_access import (
    state_string_list,
)
from app.obsidian.application.obsidian_librarian_workflow_prompts import (
    delegate_brief,
    delegate_prompt,
)
from app.obsidian.application.obsidian_note_templates import conversation_id
from app.obsidian.application.obsidian_service import ObsidianService
from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianLibrarianAsk,
    ObsidianLibrarianWorkflowResume,
)
from app.obsidian.domain.entities.obsidian_note import (
    ObsidianLibrarianWorkflow,
    ObsidianNote,
)
from app.obsidian.domain.event_enum.obsidian_enums import AlexandriaNoteType
from app.shared.exceptions import (
    LibrarianResourceNotFoundError,
    ObsidianValidationError,
)
from app.shared.types.extra_types import JSONObject
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class ObsidianLibrarianLangGraphExecutor:
    """Execute Obsidian librarian workflows through real LangGraph nodes."""

    def __init__(
        self,
        *,
        obsidian_service: ObsidianService,
        checkpoint_path: str,
        delegate_service: ObsidianLibrarianDelegateService | None = None,
    ) -> None:
        """Initialize the graph executor.

        Args:
            obsidian_service: Local Obsidian-aware librarian service.
            checkpoint_path: SQLite file path for LangGraph checkpoints.
            delegate_service: Optional GPT/OAuth-backed librarian delegate.
        """
        self._obsidian_service = obsidian_service
        self._checkpoint_path = str(Path(checkpoint_path).expanduser())
        self._delegate_service = delegate_service

    async def start(self, ask: ObsidianLibrarianAsk) -> ObsidianLibrarianGraphResult:
        """Run the graph until the approval interrupt.

        Args:
            ask: Initial librarian ask command.

        Returns:
            Graph state and workflow status.
        """
        thread_id = conversation_id()
        initial_state = initial_graph_state(
            thread_id=thread_id,
            ask=ask,
            checkpoint_path=self._checkpoint_path,
        )
        result = await self._invoke(initial_state, thread_id=thread_id)
        return result_from_graph_output(result)

    async def resume(
        self,
        workflow: ObsidianLibrarianWorkflow,
        command: ObsidianLibrarianWorkflowResume,
    ) -> ObsidianLibrarianGraphResult:
        """Resume a paused graph with approved action ids.

        Args:
            workflow: Persisted workflow checkpoint from the repository.
            command: Resume command with approved action ids.

        Returns:
            Graph state and workflow status.
        """
        resume_value: JSONObject = {"approved_actions": command.approved_actions}
        result = await self._invoke(
            Command(resume=resume_value),
            thread_id=workflow.thread_id,
        )
        return result_from_graph_output(result)

    async def delete_thread(self, thread_id: str) -> None:
        """Delete persisted LangGraph checkpoints for one workflow thread.

        Args:
            thread_id: LangGraph thread id to remove.
        """
        checkpoint = Path(self._checkpoint_path)
        if not checkpoint.exists():
            return
        async with AsyncSqliteSaver.from_conn_string(str(checkpoint)) as saver:
            await saver.adelete_thread(thread_id)

    async def _invoke(
        self,
        graph_input: ObsidianLibrarianGraphState | Command,
        *,
        thread_id: str,
    ) -> ObsidianLibrarianGraphState:
        checkpoint = Path(self._checkpoint_path)
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        async with AsyncSqliteSaver.from_conn_string(str(checkpoint)) as saver:
            graph = self._build_graph().compile(checkpointer=saver)
            result = await graph.ainvoke(
                graph_input,
                {"configurable": {"thread_id": thread_id}},
            )
        return cast(ObsidianLibrarianGraphState, result)

    def _build_graph(self) -> StateGraph:
        # Any justified: LangGraph accepts TypedDict state schemas at runtime, but its generic
        # constructor signature is currently wider than Pyrefly can infer.
        state_schema = cast(Any, ObsidianLibrarianGraphState)
        graph = StateGraph(state_schema)
        graph.add_node("collect_context", self._collect_context)
        graph.add_node("plan_actions", self._plan_actions)
        graph.add_node("approval_gate", self._approval_gate)
        graph.add_node("execute_approved_actions", self._execute_approved_actions)
        graph.add_node("finalize", self._finalize)
        graph.add_edge(START, "collect_context")
        graph.add_edge("collect_context", "plan_actions")
        graph.add_edge("plan_actions", "approval_gate")
        graph.add_edge("approval_gate", "execute_approved_actions")
        graph.add_edge("execute_approved_actions", "finalize")
        graph.add_edge("finalize", END)
        return graph

    async def _collect_context(
        self,
        state: ObsidianLibrarianGraphState,
    ) -> ObsidianLibrarianGraphState:
        ask = ask_from_state(state)
        response = await self._obsidian_service.ask_librarian(
            ObsidianLibrarianAsk(
                query=ask.query,
                active_note_path=ask.active_note_path,
                selection=ask.selection,
                project=ask.project,
                preferred_alexandria_types=ask.preferred_alexandria_types,
                max_source_refs=ask.max_source_refs,
                save_transcript=False,
                delegate_to_librarian=ask.delegate_to_librarian,
                provider_id=ask.provider_id,
                profile_id=ask.profile_id,
            )
        )
        response["conversation_id"] = state_string(state, "thread_id")
        return {"response": response, "workflow_status": "context_collected"}

    async def _plan_actions(
        self,
        state: ObsidianLibrarianGraphState,
    ) -> ObsidianLibrarianGraphState:
        pending_actions = pending_actions_from_state(state)
        return {
            "pending_actions": pending_actions,
            "approved_actions": [],
            "completed_actions": [],
            "transcript_path": None,
            "workflow_status": "approval_required",
        }

    async def _approval_gate(
        self,
        state: ObsidianLibrarianGraphState,
    ) -> ObsidianLibrarianGraphState:
        approval = interrupt(interrupt_payload(state))
        approved_action_ids = approved_actions(approval)
        return {
            "approved_actions": approved_action_ids,
            "workflow_status": "approval_resumed",
        }

    async def _execute_approved_actions(
        self,
        state: ObsidianLibrarianGraphState,
    ) -> ObsidianLibrarianGraphState:
        response = dict(state_object(state, "response"))
        completed_actions = list(state_string_list(state, "completed_actions"))
        transcript_path = state_optional_string(state, "transcript_path")
        approved = set(state_string_list(state, "approved_actions"))
        unknown_actions = approved.difference(pending_action_ids(state))
        if unknown_actions:
            unknown = ", ".join(sorted(unknown_actions))
            raise ObsidianValidationError(f"unknown workflow action: {unknown}")
        workflow = workflow_snapshot_from_state(state)
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
            note = await self._apply_graph_links(workflow, response)
            response["graph_links_path"] = note.relative_path
            completed_actions.append(f"add_graph_links:{note.relative_path}")
        delegate_payload: JSONObject | None = None
        if "ask_oauth_librarian" in approved:
            delegate_payload = await self._ask_gpt_oauth_librarian(workflow, response)
            status = delegate_status(delegate_payload, response)
            completed_actions.append(f"ask_oauth_librarian:{status}")
            response["delegate_status"] = status
            append_delegate_summary(response, delegate_payload)
        return {
            "response": response,
            "completed_actions": completed_actions,
            "transcript_path": transcript_path,
            "delegate_payload": delegate_payload,
            "workflow_status": "actions_executed",
        }

    async def _finalize(
        self,
        state: ObsidianLibrarianGraphState,
    ) -> ObsidianLibrarianGraphState:
        return {"workflow_status": "completed"}

    async def _save_transcript(
        self,
        workflow: ObsidianLibrarianWorkflow,
        response: JSONObject,
    ) -> ObsidianNote:
        body = transcript_body(workflow, response)
        refs = source_refs_from_json(response.get("source_refs"))
        return await self._obsidian_service.save_note(
            save_note_command(
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
            save_note_command(
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

    async def _apply_graph_links(
        self,
        workflow: ObsidianLibrarianWorkflow,
        response: JSONObject,
    ) -> ObsidianNote:
        active_note_path = workflow.active_note_path
        if active_note_path is None:
            raise ObsidianValidationError("active note is required for graph links")
        return await self._obsidian_service.apply_librarian_graph_links(
            active_note_path=active_note_path,
            response=response,
        )

    async def _ask_gpt_oauth_librarian(
        self,
        workflow: ObsidianLibrarianWorkflow,
        response: JSONObject,
    ) -> JSONObject | None:
        if self._delegate_service is None:
            return None
        command = HermesLibrarianAskCommand(
            prompt=delegate_prompt(workflow, response),
            agent_name="obsidian-librarian",
            project=workflow.project,
            task_summary=workflow.query,
            delegate_to_librarian=True,
            provider_id=workflow.provider_id,
            librarian_profile_id=workflow.profile_id,
            librarian_model=None,
            librarian_role_prompt=None,
            max_librarian_agents=1,
            routing_specialties=["obsidian", "graph", "oauth", "gpt"],
            source_refs=source_refs(response),
            librarian_brief=delegate_brief(workflow, response),
        )
        try:
            payload = await self._delegate_service.ask_librarian(command)
        except LibrarianResourceNotFoundError as error:
            return delegate_unavailable_payload(workflow, str(error))
        return cast(JSONObject, dict(payload))
