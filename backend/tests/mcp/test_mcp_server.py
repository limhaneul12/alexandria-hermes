"""MCP server tests for HTTP-only Alexandria tools."""

from __future__ import annotations

from collections.abc import Awaitable
from inspect import iscoroutinefunction

import anyio
import httpx
from app.mcp_server.backend_api_client import (
    AlexandriaApiClient,
    AlexandriaApiSettings,
)
from app.mcp_server.backend_tool_gateway import (
    alexandria_archive_context,
    alexandria_capture_context,
    alexandria_get_prompt,
    alexandria_get_skill,
    alexandria_rag_status,
    alexandria_search,
    alexandria_submit_skill_candidate,
)
from app.mcp_server.server_runtime import create_mcp_server
from app.shared.serialization.orjson_codec import dumps_json, loads_json
from app.shared.types.extra_types import JSONValue

RecordedCall = httpx.Request


def _client() -> tuple[AlexandriaApiClient, list[RecordedCall]]:
    calls: list[RecordedCall] = []

    async def fake_transport(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, content=dumps_json({"ok": True}))

    client = AlexandriaApiClient(
        AlexandriaApiSettings(
            base_url="http://backend:8000",
            api_token="secret-token",
            timeout=12.0,
        ),
        transport=httpx.MockTransport(fake_transport),
    )
    return client, calls


async def _await_json(awaitable: Awaitable[JSONValue]) -> JSONValue:
    result = await awaitable
    return result


def _run_json(awaitable: Awaitable[JSONValue]) -> JSONValue:
    result = anyio.run(_await_json, awaitable)
    return result


def test_mcp_backend_tool_gateway_are_async_http_boundaries() -> None:
    """MCP tool HTTP calls should expose async handlers to FastMCP."""
    assert iscoroutinefunction(alexandria_search)
    assert iscoroutinefunction(alexandria_capture_context)
    assert iscoroutinefunction(alexandria_rag_status)


def test_mcp_client_sends_backend_http_only_with_auth_header() -> None:
    """MCP client should call the backend URL and attach bearer auth only."""
    client, calls = _client()

    payload = _run_json(
        alexandria_search(client, "context recall", limit=3, strategy="FTS_ONLY")
    )

    request = calls[0]
    request_body = loads_json(request.content or b"{}")
    assert payload == {"ok": True}
    assert request.method == "POST"
    assert str(request.url) == "http://backend:8000/library/contexts/search"
    assert request.headers["accept"] == "application/json"
    assert request.headers["content-type"] == "application/json"
    assert request.headers["authorization"] == "Bearer secret-token"
    assert request_body == {
        "query": "context recall",
        "strategy": "FTS_ONLY",
        "limit": 3,
    }


def test_mcp_tools_map_to_non_destructive_backend_endpoints() -> None:
    """MCP tools should expose capture/status/archive without hard-delete calls."""
    client, calls = _client()

    async def run_tools() -> None:
        await alexandria_capture_context(
            client, title="Handoff", content="## Summary\nDone"
        )
        await alexandria_archive_context(client, "ctx-1")
        await alexandria_rag_status(client)
        await alexandria_submit_skill_candidate(
            client,
            title="FastAPI skill",
            purpose="Use dependency overrides",
            content="# FastAPI",
        )

    anyio.run(run_tools)

    methods_and_paths = [
        (request.method, str(request.url).removeprefix("http://backend:8000"))
        for request in calls
    ]
    assert methods_and_paths == [
        ("POST", "/library/contexts/capture"),
        ("POST", "/library/contexts/ctx-1/archive"),
        ("GET", "/library/contexts/rag/status"),
        ("POST", "/skills/submit-by-agent"),
    ]
    assert all(method != "DELETE" for method, _ in methods_and_paths)


def test_mcp_capture_marks_agent_authored_context_explicitly() -> None:
    """MCP capture should not rely on implicit backend source-type defaults."""
    client, calls = _client()

    _run_json(
        alexandria_capture_context(client, title="Handoff", content="## Summary\nDone")
    )

    request_body = loads_json(calls[0].content or b"{}")
    assert request_body["source_type"] == "AGENT"


def test_mcp_path_parameters_are_percent_encoded() -> None:
    """MCP path arguments should remain a single backend path segment."""
    client, calls = _client()

    async def run_tools() -> None:
        await alexandria_archive_context(client, "ctx/1?archive=false")
        await alexandria_get_skill(client, "skill/1#anchor")
        await alexandria_get_prompt(client, "prompt/1?raw=true")

    anyio.run(run_tools)

    paths = [str(request.url).removeprefix("http://backend:8000") for request in calls]
    assert paths == [
        "/library/contexts/ctx%2F1%3Farchive%3Dfalse/archive",
        "/skills/skill%2F1%23anchor",
        "/prompts/prompt%2F1%3Fraw%3Dtrue",
    ]


def test_fastmcp_server_registers_required_alexandria_tools() -> None:
    """FastMCP registration should expose the G005 tool contract names."""
    client, _ = _client()
    server = create_mcp_server(client=client)

    tools = anyio.run(server.list_tools)

    names = {tool.name for tool in tools}
    assert {
        "alexandria_search",
        "alexandria_get_skill",
        "alexandria_get_prompt",
        "alexandria_recall_context",
        "alexandria_rag_context",
        "alexandria_capture_context",
        "alexandria_prepare_compact",
        "alexandria_request_skill_acquisition",
        "alexandria_submit_skill_candidate",
        "alexandria_archive_context",
        "alexandria_rag_status",
    } <= names
