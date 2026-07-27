"""Register operational readiness and recovery MCP tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.mcp_server.backend_api_client import AlexandriaApiClient
from app.mcp_server.tools.backend_gateway_policy import DEFAULT_SOURCE_AGENT
from app.mcp_server.tools.operations_backend_gateway import (
    alexandria_operational_readiness,
    alexandria_recovery_plan,
    alexandria_recovery_quarantine,
    alexandria_recovery_retry,
    alexandria_recovery_run,
    alexandria_recovery_run_status,
)
from app.shared.types.extra_types import JSONValue


def register_operations_tools(server: FastMCP, api_client: AlexandriaApiClient) -> None:
    """Register operational readiness and recovery MCP tools.

    Args:
        server: FastMCP server receiving tool registrations.
        api_client: Backend HTTP API client used by tool callbacks.
    """

    @server.tool(name="alexandria_operational_readiness")
    async def _tool_operational_readiness() -> JSONValue:
        """Read operational database, vault, and RAG readiness.

        Returns:
            Backend operational readiness response.
        """
        return await alexandria_operational_readiness(api_client)

    @server.tool(name="alexandria_recovery_plan")
    async def _tool_recovery_plan(
        trigger: str = "manual",
        actor: str = DEFAULT_SOURCE_AGENT,
        idempotency_key: str | None = None,
        parent_run_id: str | None = None,
    ) -> JSONValue:
        """Build a read-only operational recovery dry-run plan.

        Args:
            trigger: Recovery plan trigger source.
            actor: Operator or agent requesting the plan.
            idempotency_key: Optional idempotency key.
            parent_run_id: Optional parent recovery run identifier.

        Returns:
            Backend recovery dry-run plan response.
        """
        return await alexandria_recovery_plan(
            api_client,
            trigger,
            actor,
            idempotency_key,
            parent_run_id,
        )

    @server.tool(name="alexandria_recovery_run")
    async def _tool_recovery_run(
        idempotency_key: str,
        trigger: str = "manual",
        actor: str = DEFAULT_SOURCE_AGENT,
        parent_run_id: str | None = None,
    ) -> JSONValue:
        """Start or return an idempotent operational recovery run.

        Args:
            idempotency_key: Required idempotency key for the explicit apply.
            trigger: Recovery run trigger source.
            actor: Operator or agent requesting recovery.
            parent_run_id: Optional parent recovery run identifier.

        Returns:
            Backend recovery run response.
        """
        return await alexandria_recovery_run(
            api_client,
            trigger=trigger,
            actor=actor,
            idempotency_key=idempotency_key,
            parent_run_id=parent_run_id,
        )

    @server.tool(name="alexandria_recovery_run_status")
    async def _tool_recovery_run_status(run_id: str) -> JSONValue:
        """Return a persisted operational recovery run by id.

        Args:
            run_id: Recovery run identifier.

        Returns:
            Backend recovery run response.
        """
        return await alexandria_recovery_run_status(
            api_client,
            run_id,
        )

    @server.tool(name="alexandria_recovery_retry")
    async def _tool_recovery_retry(
        run_id: str,
        trigger: str = "retry",
        actor: str = DEFAULT_SOURCE_AGENT,
        idempotency_key: str | None = None,
    ) -> JSONValue:
        """Start or return a parent-linked operational recovery retry.

        Args:
            run_id: Parent recovery run identifier.
            trigger: Recovery retry trigger source.
            actor: Operator or agent requesting retry.
            idempotency_key: Optional retry idempotency key.

        Returns:
            Backend recovery retry response.
        """
        return await alexandria_recovery_retry(
            api_client,
            run_id,
            trigger,
            actor,
            idempotency_key,
        )

    @server.tool(name="alexandria_recovery_quarantine")
    async def _tool_recovery_quarantine() -> JSONValue:
        """Return stored recovery quarantine artifacts.

        Returns:
            Backend recovery quarantine inventory response.
        """
        return await alexandria_recovery_quarantine(api_client)
