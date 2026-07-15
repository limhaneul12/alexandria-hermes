"""MCP HTTP tool adapters for Memory Compact artifacts."""

from __future__ import annotations

from urllib.parse import quote

from app.mcp_server.backend_api_client import AlexandriaApiClient
from app.memory.domain.event_enum.memory_compact_enums import MemoryCompactStatus
from app.shared.types.extra_types import JSONObject, JSONValue


async def alexandria_list_memory_compact_artifacts(
    client: AlexandriaApiClient,
    project: str | None = None,
    status: MemoryCompactStatus | None = None,
    limit: int = 20,
    offset: int = 0,
) -> JSONValue:
    """List durable Memory Compact artifacts.

    Args:
        client: Backend HTTP client.
        project: Optional project filter.
        status: Optional lifecycle status filter.
        limit: Maximum number of rows to return.
        offset: Number of rows to skip.

    Returns:
        Backend Memory Compact list response.
    """
    query: JSONObject = {
        "limit": min(max(int(limit), 1), 50),
        "offset": max(int(offset), 0),
    }
    if project is not None:
        query["project"] = project
    if status is not None:
        query["status"] = status.value
    return await client.get("/memory/compacts", params=query)


async def alexandria_create_memory_compact(
    client: AlexandriaApiClient,
    covered_from: str,
    covered_to: str,
    markdown_body: str,
    project: str | None = None,
    status: MemoryCompactStatus = MemoryCompactStatus.DRAFT,
    source_refs: list[dict[str, str]] | None = None,
) -> JSONValue:
    """Create a durable Memory Compact artifact.

    Args:
        client: Backend HTTP client.
        covered_from: Inclusive coverage start timestamp.
        covered_to: Exclusive coverage end timestamp.
        markdown_body: Durable Markdown body for the compact.
        project: Optional project filter.
        status: Compact lifecycle status.
        source_refs: Optional source references for CURRENT compacts.

    Returns:
        Backend Memory Compact response.
    """
    payload: JSONObject = {
        "covered_from": covered_from,
        "covered_to": covered_to,
        "markdown_body": markdown_body,
        "status": status.value,
        "source_refs": _source_ref_payloads(source_refs),
    }
    if project is not None:
        payload["project"] = project
    return await client.post("/memory/compacts", payload)


async def alexandria_get_current_memory_compact(
    client: AlexandriaApiClient,
    project: str | None = None,
) -> JSONValue:
    """Read the current Memory Compact for a project.

    Args:
        client: Backend HTTP client.
        project: Optional project filter.

    Returns:
        Backend Memory Compact response.
    """
    query: JSONObject | None = None if project is None else {"project": project}
    return await client.get("/memory/compacts/current", params=query)


async def alexandria_get_memory_compact(
    client: AlexandriaApiClient,
    compact_id: str,
) -> JSONValue:
    """Read one selected Memory Compact by id.

    Args:
        client: Backend HTTP client.
        compact_id: Memory Compact identifier.

    Returns:
        Backend Memory Compact response.
    """
    return await client.get(f"/memory/compacts/{quote(compact_id, safe='')}")


async def alexandria_delete_memory_compact(
    client: AlexandriaApiClient,
    compact_id: str,
) -> JSONValue:
    """Hard delete one selected Memory Compact by id.

    Args:
        client: Backend HTTP client.
        compact_id: Memory Compact identifier.

    Returns:
        Backend delete response, typically None for HTTP 204.
    """
    return await client.delete(f"/memory/compacts/{quote(compact_id, safe='')}")


async def alexandria_mark_memory_compact_current(
    client: AlexandriaApiClient,
    compact_id: str,
) -> JSONValue:
    """Promote one compact to CURRENT.

    Args:
        client: Backend HTTP client.
        compact_id: Memory Compact identifier.

    Returns:
        Backend Memory Compact response.
    """
    return await client.post(
        f"/memory/compacts/{quote(compact_id, safe='')}/mark-current", {}
    )


async def alexandria_archive_memory_compact(
    client: AlexandriaApiClient,
    compact_id: str,
) -> JSONValue:
    """Archive one selected Memory Compact by id without deleting it.

    Args:
        client: Backend HTTP client.
        compact_id: Memory Compact identifier.

    Returns:
        Backend Memory Compact response.
    """
    return await client.post(
        f"/memory/compacts/{quote(compact_id, safe='')}/archive", {}
    )


def _source_ref_payloads(source_refs: list[dict[str, str]] | None) -> list[JSONObject]:
    if source_refs is None:
        return []
    return [
        {
            "source_type": source_ref["source_type"],
            "source_id": source_ref["source_id"],
            "title": source_ref["title"],
            "detail_path": source_ref["detail_path"],
        }
        for source_ref in source_refs
    ]
