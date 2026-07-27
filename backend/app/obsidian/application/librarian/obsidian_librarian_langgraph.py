"""LangGraph executor for resumable Obsidian librarian workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from app.obsidian.application.librarian.obsidian_librarian_action_executor import (
    ObsidianLibrarianActionExecutor,
)
from app.obsidian.application.librarian.obsidian_librarian_graph_contracts import (
    ObsidianLibrarianDelegateService,
    ObsidianLibrarianGraphResult,
    ObsidianLibrarianGraphState,
)
from app.obsidian.application.librarian.obsidian_librarian_graph_nodes import (
    ObsidianLibrarianGraphNodes,
)
from app.obsidian.application.librarian.obsidian_librarian_graph_state_codec import (
    _initial_graph_state as initial_graph_state,
    _result_from_graph_output as result_from_graph_output,
)
from app.obsidian.application.notes.obsidian_note_templates import conversation_id
from app.obsidian.application.service.obsidian_service import ObsidianService
from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianLibrarianAsk,
    ObsidianLibrarianWorkflowResume,
)
from app.obsidian.domain.entities.obsidian_note import (
    ObsidianLibrarianWorkflow,
)
from app.shared.types.extra_types import JSONObject
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command


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
        self._action_executor = ObsidianLibrarianActionExecutor(
            obsidian_service=obsidian_service,
            delegate_service=delegate_service,
        )
        self._nodes = ObsidianLibrarianGraphNodes(
            obsidian_service=obsidian_service,
            action_executor=self._action_executor,
        )

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
        resume_value: JSONObject = {"approved_actions": list(command.approved_actions)}
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
        # Any justified: isolated to this third-party constructor boundary. LangGraph
        # accepts TypedDict state classes at runtime, but its public typing does
        # not expose the internal StateLike alias required by Pyrefly.
        state_schema = cast(Any, ObsidianLibrarianGraphState)
        graph = StateGraph(state_schema)
        graph.add_node("collect_context", self._nodes.collect_context)
        graph.add_node("plan_actions", self._nodes.plan_actions)
        graph.add_node("approval_gate", self._nodes.approval_gate)
        graph.add_node("execute_approved_actions", self._nodes.execute_approved_actions)
        graph.add_node("finalize", self._nodes.finalize)
        graph.add_edge(START, "collect_context")
        graph.add_edge("collect_context", "plan_actions")
        graph.add_edge("plan_actions", "approval_gate")
        graph.add_edge("approval_gate", "execute_approved_actions")
        graph.add_edge("execute_approved_actions", "finalize")
        graph.add_edge("finalize", END)
        return graph
