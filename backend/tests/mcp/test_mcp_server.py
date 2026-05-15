"""MCP server tests for HTTP-only Alexandria tools."""

from __future__ import annotations

from collections.abc import Awaitable
from inspect import iscoroutinefunction

import anyio
import httpx
import pytest
from app.mcp_server.backend_api_client import (
    AlexandriaApiClient,
    AlexandriaApiSettings,
)
from app.mcp_server.backend_tool_gateway import (
    alexandria_archive_context,
    alexandria_ask_librarian,
    alexandria_capture_context,
    alexandria_get_prompt,
    alexandria_get_skill,
    alexandria_librarian_job_status,
    alexandria_librarian_oauth_poll,
    alexandria_librarian_oauth_refresh,
    alexandria_librarian_oauth_start,
    alexandria_librarian_oauth_status,
    alexandria_librarian_route_preview,
    alexandria_rag_status,
    alexandria_record_usage,
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
            operator_api_key="operator-secret",
            timeout=12.0,
        ),
        transport=httpx.MockTransport(fake_transport),
    )
    return client, calls


def _client_with_payload(
    response_payload: JSONValue,
) -> tuple[AlexandriaApiClient, list[RecordedCall]]:
    calls: list[RecordedCall] = []

    async def fake_transport(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, content=dumps_json(response_payload))

    client = AlexandriaApiClient(
        AlexandriaApiSettings(
            base_url="http://backend:8000",
            api_token="secret-token",
            operator_api_key="operator-secret",
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
    assert iscoroutinefunction(alexandria_record_usage)
    assert iscoroutinefunction(alexandria_ask_librarian)
    assert iscoroutinefunction(alexandria_librarian_job_status)
    assert iscoroutinefunction(alexandria_librarian_oauth_start)
    assert iscoroutinefunction(alexandria_librarian_oauth_poll)
    assert iscoroutinefunction(alexandria_librarian_oauth_status)
    assert iscoroutinefunction(alexandria_librarian_oauth_refresh)
    assert iscoroutinefunction(alexandria_librarian_route_preview)


def test_mcp_client_sends_backend_http_only_with_auth_headers() -> None:
    """MCP client should call the backend URL and attach auth headers."""
    client, calls = _client()

    payload = _run_json(
        alexandria_search(client, "context recall", limit=3, strategy="FTS_ONLY")
    )

    request = calls[0]
    request_body = loads_json(request.content or b"{}")
    assert payload == {"ok": True}
    assert request.method == "POST"
    assert str(request.url) == "http://backend:8000/memory/contexts/retrieval/search"
    assert request.headers["accept"] == "application/json"
    assert request.headers["content-type"] == "application/json"
    assert request.headers["authorization"] == "Bearer secret-token"
    assert request.headers["x-alexandria-operator-key"] == "operator-secret"
    assert request_body == {
        "query": "context recall",
        "strategy": "FTS_ONLY",
        "limit": 3,
    }


def test_mcp_settings_use_api_token_as_operator_key_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MCP env loading should keep generated legacy API-token snippets usable."""
    monkeypatch.delenv("ALEXANDRIA_OPERATOR_API_KEY", raising=False)
    monkeypatch.delenv("SERVICE_OPERATOR_API_KEY", raising=False)
    monkeypatch.setenv("ALEXANDRIA_API_TOKEN", "legacy-token")

    settings = AlexandriaApiSettings.from_env()

    assert settings.api_token == "legacy-token"
    assert settings.operator_api_key == "legacy-token"


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
        ("POST", "/memory/contexts/capture"),
        ("POST", "/memory/contexts/ctx-1/archive"),
        ("GET", "/memory/contexts/rag/status"),
        ("POST", "/library/skills/submit-by-agent"),
    ]
    assert all(method != "DELETE" for method, _ in methods_and_paths)


def test_mcp_submit_skill_candidate_sends_self_acquisition_evidence() -> None:
    """Skill candidate tool should forward Hermes research evidence."""
    client, calls = _client()

    _run_json(
        alexandria_submit_skill_candidate(
            client,
            title="FastAPI skill",
            purpose="Use dependency overrides",
            content="# FastAPI",
            evidence_urls=["https://example.com/fastapi-skill"],
            source_summary="Hermes researched the gap directly.",
        )
    )

    request_body = loads_json(calls[0].content or b"{}")
    assert calls[0].method == "POST"
    assert str(calls[0].url) == "http://backend:8000/library/skills/submit-by-agent"
    assert request_body["evidence_urls"] == ["https://example.com/fastapi-skill"]
    assert request_body["source_summary"] == "Hermes researched the gap directly."


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
        "/memory/contexts/ctx%2F1%3Farchive%3Dfalse/archive",
        "/library/skills/skill%2F1%23anchor",
        "/library/prompts/prompt%2F1%3Fraw%3Dtrue",
    ]


def test_mcp_collaboration_tools_map_to_backend_contracts() -> None:
    """MCP collaboration tools should call usage and librarian APIs only."""
    client, calls = _client()

    async def run_tools() -> None:
        await alexandria_record_usage(
            client,
            item_id="skill-1",
            item_type="SKILL",
            selection_source="SEARCH",
            query="oauth skill",
            project="alexandria-hermes",
            task_summary="Implement OAuth",
        )
        await alexandria_ask_librarian(
            client,
            prompt="Need OAuth skill",
            delegate_to_librarian=True,
            project="alexandria-hermes",
            librarian_profile_id="profile-1",
            librarian_model="gpt-5.5",
            librarian_role_prompt="Use project memory first.",
            max_librarian_agents=2,
        )
        await alexandria_librarian_route_preview(
            client,
            prompt="Need OAuth skill",
            project="alexandria-hermes",
            librarian_profile_id="profile-1",
        )
        await alexandria_librarian_job_status(client, "job/1")

    anyio.run(run_tools)

    methods_and_paths = [
        (request.method, str(request.url).removeprefix("http://backend:8000"))
        for request in calls
    ]
    usage_body = loads_json(calls[0].content or b"{}")
    ask_body = loads_json(calls[1].content or b"{}")
    route_preview_body = loads_json(calls[2].content or b"{}")
    assert methods_and_paths == [
        ("POST", "/library/usage"),
        ("POST", "/librarians/ask"),
        ("POST", "/librarians/route-preview"),
        ("GET", "/librarians/jobs/job%2F1"),
    ]
    assert usage_body == {
        "item_id": "skill-1",
        "item_type": "SKILL",
        "agent_name": "Hermes",
        "query": "oauth skill",
        "selection_source": "SEARCH",
        "success": True,
        "feedback": {
            "project": "alexandria-hermes",
            "task_summary": "Implement OAuth",
        },
    }
    assert ask_body == {
        "prompt": "Need OAuth skill",
        "agent_name": "Hermes",
        "project": "alexandria-hermes",
        "delegate_to_librarian": True,
        "librarian_profile_id": "profile-1",
        "librarian_model": "gpt-5.5",
        "librarian_role_prompt": "Use project memory first.",
        "max_librarian_agents": 2,
        "routing_specialties": [],
    }
    assert route_preview_body == {
        "prompt": "Need OAuth skill",
        "agent_name": "Hermes",
        "project": "alexandria-hermes",
        "delegate_to_librarian": False,
        "librarian_profile_id": "profile-1",
        "routing_specialties": [],
    }


def test_mcp_librarian_oauth_tools_map_to_safe_backend_lifecycle() -> None:
    """MCP OAuth lifecycle tools should call provider routes without leaking codes."""
    client, calls = _client_with_payload(
        {
            "provider_id": "provider-1",
            "status": "pending",
            "user_code": "SECRET-CODE",
            "verification_uri": "https://login.example/device",
            "verification_uri_complete": (
                "https://login.example/device?user_code=SECRET-CODE"
            ),
            "oauth_access_token": "secret-token",
            "connected": False,
        }
    )

    async def run_tools() -> list[JSONValue]:
        return [
            await alexandria_librarian_oauth_start(client, "provider/1"),
            await alexandria_librarian_oauth_poll(client, "provider/1"),
            await alexandria_librarian_oauth_status(client, "provider/1"),
            await alexandria_librarian_oauth_refresh(client, "provider/1"),
        ]

    payloads = anyio.run(run_tools)

    methods_and_paths = [
        (request.method, str(request.url).removeprefix("http://backend:8000"))
        for request in calls
    ]
    serialized_payloads = dumps_json(payloads).decode("utf-8")
    assert methods_and_paths == [
        ("POST", "/settings/connections/provider%2F1/oauth/start"),
        ("POST", "/settings/connections/provider%2F1/oauth/poll"),
        ("GET", "/settings/connections/provider%2F1/oauth/status"),
        ("POST", "/settings/connections/provider%2F1/oauth/refresh"),
    ]
    assert "SECRET-CODE" not in serialized_payloads
    assert "verification_uri_complete" not in serialized_payloads
    assert "oauth_access_token" not in serialized_payloads


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
        "alexandria_record_usage",
        "alexandria_ask_librarian",
        "alexandria_librarian_route_preview",
        "alexandria_librarian_job_status",
        "alexandria_librarian_oauth_start",
        "alexandria_librarian_oauth_poll",
        "alexandria_librarian_oauth_status",
        "alexandria_librarian_oauth_refresh",
        "alexandria_archive_context",
        "alexandria_rag_status",
    } <= names
