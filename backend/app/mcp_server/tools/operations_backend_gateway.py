"""Operational readiness and recovery MCP HTTP gateway functions."""

from __future__ import annotations

from app.mcp_server.backend_api_client import AlexandriaApiClient
from app.mcp_server.tools.backend_gateway_policy import (
    DEFAULT_SOURCE_AGENT,
    _path_segment,
    _required_recovery_run_idempotency_key,
)
from app.shared.types.extra_types import JSONObject, JSONValue


async def alexandria_operational_readiness(
    client: AlexandriaApiClient,
) -> JSONValue:
    """Read operational database, vault, and RAG readiness.

    Args:
        client: Backend HTTP client.

    Returns:
        Operational readiness response.
    """
    response = await client.get("/operations/readiness")
    return response


async def alexandria_recovery_plan(
    client: AlexandriaApiClient,
    trigger: str = "manual",
    actor: str = DEFAULT_SOURCE_AGENT,
    idempotency_key: str | None = None,
    parent_run_id: str | None = None,
) -> JSONValue:
    """Build a read-only operational recovery dry-run plan.

    Args:
        client: Backend HTTP client.
        trigger: Recovery plan trigger source.
        actor: Operator or agent requesting the plan.
        idempotency_key: Optional idempotency key.
        parent_run_id: Optional parent recovery run identifier.

    Returns:
        Recovery dry-run plan response.
    """
    payload: JSONObject = {
        "trigger": trigger,
        "actor": actor,
    }
    if idempotency_key is not None:
        payload["idempotency_key"] = idempotency_key
    if parent_run_id is not None:
        payload["parent_run_id"] = parent_run_id
    response = await client.post("/operations/recovery/plan", payload)
    return response


async def alexandria_recovery_run(
    client: AlexandriaApiClient,
    trigger: str = "manual",
    actor: str = DEFAULT_SOURCE_AGENT,
    idempotency_key: str | None = None,
    parent_run_id: str | None = None,
) -> JSONValue:
    """Start or return an idempotent operational recovery run.

    Args:
        client: Backend HTTP client.
        trigger: Recovery run trigger source.
        actor: Operator or agent requesting recovery.
        idempotency_key: Required idempotency key for the explicit apply.
        parent_run_id: Optional parent recovery run identifier.

    Returns:
        Recovery run response.
    """
    required_idempotency_key = _required_recovery_run_idempotency_key(idempotency_key)
    payload: JSONObject = {
        "trigger": trigger,
        "actor": actor,
        "idempotency_key": required_idempotency_key,
    }
    if parent_run_id is not None:
        payload["parent_run_id"] = parent_run_id
    response = await client.post("/operations/recovery/runs", payload)
    return response


async def alexandria_recovery_run_status(
    client: AlexandriaApiClient,
    run_id: str,
) -> JSONValue:
    """Return a persisted operational recovery run by id.

    Args:
        client: Backend HTTP client.
        run_id: Recovery run identifier.

    Returns:
        Recovery run response.
    """
    response = await client.get(f"/operations/recovery/runs/{_path_segment(run_id)}")
    return response


async def alexandria_recovery_retry(
    client: AlexandriaApiClient,
    run_id: str,
    trigger: str = "retry",
    actor: str = DEFAULT_SOURCE_AGENT,
    idempotency_key: str | None = None,
) -> JSONValue:
    """Start or return a parent-linked operational recovery retry.

    Args:
        client: Backend HTTP client.
        run_id: Parent recovery run identifier.
        trigger: Recovery retry trigger source.
        actor: Operator or agent requesting retry.
        idempotency_key: Optional retry idempotency key.

    Returns:
        Recovery retry run response.
    """
    payload: JSONObject = {
        "trigger": trigger,
        "actor": actor,
    }
    if idempotency_key is not None:
        payload["idempotency_key"] = idempotency_key
    response = await client.post(
        f"/operations/recovery/runs/{_path_segment(run_id)}/retry",
        payload,
    )
    return response


async def alexandria_recovery_quarantine(
    client: AlexandriaApiClient,
) -> JSONValue:
    """Return stored recovery quarantine artifacts.

    Args:
        client: Backend HTTP client.

    Returns:
        Recovery quarantine inventory response.
    """
    response = await client.get("/operations/recovery/quarantine")
    return response
