"""MCP server tests for HTTP-only Alexandria tools."""

from __future__ import annotations

from collections.abc import Awaitable
from inspect import iscoroutinefunction

import anyio
import httpx
import pytest
from app.main import app
from app.mcp_server.backend_api_client import (
    AlexandriaApiClient,
    AlexandriaApiSettings,
)
from app.mcp_server.backend_tool_gateway import (
    alexandria_archive_context,
    alexandria_ask_librarian,
    alexandria_ask_obsidian_librarian,
    alexandria_complete_skill_acquisition,
    alexandria_delete_context,
    alexandria_delete_memory_compact,
    alexandria_get_current_memory_compact,
    alexandria_get_memory_compact,
    alexandria_get_related_notes,
    alexandria_librarian_brief_preview,
    alexandria_librarian_job_status,
    alexandria_librarian_oauth_poll,
    alexandria_librarian_oauth_refresh,
    alexandria_librarian_oauth_start,
    alexandria_librarian_oauth_status,
    alexandria_librarian_route_preview,
    alexandria_list_memory_compact_artifacts,
    alexandria_rag_status,
    alexandria_read_note,
    alexandria_reindex_vault,
    alexandria_save_note,
    alexandria_search,
    alexandria_search_vault,
    alexandria_skill_acquisition_job_status,
    alexandria_start_skill_acquisition,
)
from app.mcp_server.server_runtime import build_mcp_server
from app.memory.domain.event_enum.memory_compact_enums import (
    MemoryCompactStatus,
)
from app.platform.security.operator_api_key import OPERATOR_API_KEY_HEADER
from app.shared.serialization.orjson_codec import dumps_json, loads_json
from app.shared.types.extra_types import JSONValue
from fastapi.testclient import TestClient

RecordedCall = httpx.Request


def _client() -> tuple[AlexandriaApiClient, list[RecordedCall]]:
    calls: list[RecordedCall] = []

    async def fake_transport(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, content=dumps_json({"ok": True}))

    client = AlexandriaApiClient(
        AlexandriaApiSettings(
            base_url="http://backend:8000",
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
    async_tools = [
        alexandria_search,
        alexandria_search_vault,
        alexandria_archive_context,
        alexandria_delete_context,
        alexandria_rag_status,
        alexandria_read_note,
        alexandria_get_related_notes,
        alexandria_reindex_vault,
        alexandria_ask_librarian,
        alexandria_librarian_brief_preview,
        alexandria_librarian_job_status,
        alexandria_librarian_oauth_start,
        alexandria_librarian_oauth_poll,
        alexandria_librarian_oauth_status,
        alexandria_librarian_oauth_refresh,
        alexandria_librarian_route_preview,
        alexandria_ask_obsidian_librarian,
        alexandria_list_memory_compact_artifacts,
        alexandria_start_skill_acquisition,
        alexandria_save_note,
        alexandria_skill_acquisition_job_status,
        alexandria_complete_skill_acquisition,
        alexandria_get_current_memory_compact,
        alexandria_get_memory_compact,
        alexandria_delete_memory_compact,
    ]

    assert all(iscoroutinefunction(tool) for tool in async_tools)


def test_mcp_client_sends_backend_http_only_with_auth_headers() -> None:
    """MCP client should call the backend URL and attach the operator header."""
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
    assert "authorization" not in request.headers
    assert request.headers["X-Alexandria-Operator-Key"] == "operator-secret"
    assert request_body == {
        "query": "context recall",
        "strategy": "FTS_ONLY",
        "limit": 3,
    }


def test_mcp_settings_ignore_legacy_api_token_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MCP env loading should not treat the legacy token as operator authority."""
    legacy_token_name = "ALEXANDRIA_" + "API_TOKEN"
    monkeypatch.setenv("ALEXANDRIA_OPERATOR_API_KEY", "")
    monkeypatch.setenv(legacy_token_name, "legacy-token")

    settings = AlexandriaApiSettings.from_env()

    assert settings.operator_api_key is None


def test_mcp_tools_map_to_non_destructive_backend_endpoints() -> None:
    """MCP tools should expose status/archive without deleted CRUD calls."""
    client, calls = _client()

    async def run_tools() -> None:
        await alexandria_archive_context(client, "ctx-1")
        await alexandria_rag_status(client)

    anyio.run(run_tools)

    methods_and_paths = [
        (request.method, str(request.url).removeprefix("http://backend:8000"))
        for request in calls
    ]
    assert methods_and_paths == [
        ("POST", "/memory/contexts/ctx-1/archive"),
        ("GET", "/memory/contexts/rag/status"),
    ]
    assert all(method != "DELETE" for method, _ in methods_and_paths)


def test_mcp_async_skill_acquisition_tools_use_durable_job_endpoints() -> None:
    """Async skill-acquisition tools should use durable job APIs."""
    client, calls = _client()

    async def run_tools() -> None:
        await alexandria_start_skill_acquisition(
            client,
            prompt="Need browser automation skill",
            project="alexandria-hermes",
            task_summary="Browser test blocked.",
            provider_id="provider-1",
        )
        await alexandria_skill_acquisition_job_status(client, "job/1")
        await alexandria_complete_skill_acquisition(
            client,
            job_id="job/1",
            title="Browser automation skill",
            purpose="Automate browser checks safely.",
            content="Use stable selectors and bounded waits.",
            evidence_urls=["https://example.com/browser"],
            source_summary="Provider returned a sanitized artifact.",
            next_steps=["Retry the blocked browser test."],
            tags=["browser"],
            required_tools=["playwright"],
        )

    anyio.run(run_tools)

    methods_and_paths = [
        (request.method, str(request.url).removeprefix("http://backend:8000"))
        for request in calls
    ]
    start_body = loads_json(calls[0].content or b"{}")
    completion_body = loads_json(calls[2].content or b"{}")
    assert methods_and_paths == [
        ("POST", "/librarians/skill-acquisition-jobs"),
        ("GET", "/librarians/skill-acquisition-jobs/job%2F1"),
        ("POST", "/librarians/skill-acquisition-jobs/job%2F1/complete"),
    ]
    assert start_body == {
        "prompt": "Need browser automation skill",
        "agent_name": "Hermes",
        "project": "alexandria-hermes",
        "task_summary": "Browser test blocked.",
        "provider_id": "provider-1",
    }
    assert completion_body["title"] == "Browser automation skill"
    assert completion_body["evidence_urls"] == ["https://example.com/browser"]
    assert completion_body["next_steps"] == ["Retry the blocked browser test."]
    assert completion_body["required_tools"] == ["playwright"]


def test_mcp_skill_acquisition_status_polling_returns_job_status() -> None:
    """Polling should return sanitized job status without Context Vault writes."""
    calls: list[RecordedCall] = []
    responses: list[JSONValue] = [
        {
            "id": "job/1",
            "status": "ACCEPTED",
            "result_available": False,
            "secret": "provider-secret-material",
            "token": "secret-token",
        },
        {
            "id": "job/1",
            "status": "ACCEPTED",
            "result_available": False,
            "error_message": None,
        },
        {
            "id": "job/1",
            "status": "COMPLETED",
            "skill_id": None,
            "context_id": None,
            "result_available": True,
            "error_message": None,
            "secret": "provider-secret-material",
            "token": "secret-token",
        },
    ]

    async def fake_transport(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        payload = responses[len(calls) - 1]
        return httpx.Response(200, content=dumps_json(payload))

    client = AlexandriaApiClient(
        AlexandriaApiSettings(
            base_url="http://backend:8000",
            operator_api_key="operator-secret",
            timeout=12.0,
        ),
        transport=httpx.MockTransport(fake_transport),
    )

    async def run_tools() -> tuple[JSONValue, JSONValue, JSONValue]:
        start_response = await alexandria_start_skill_acquisition(
            client,
            prompt="Need browser automation skill",
        )
        status_pending = await alexandria_skill_acquisition_job_status(client, "job/1")
        status_complete = await alexandria_skill_acquisition_job_status(client, "job/1")
        return start_response, status_pending, status_complete

    start_response, status_pending, status_complete = anyio.run(run_tools)

    methods_and_paths = [
        (request.method, str(request.url).removeprefix("http://backend:8000"))
        for request in calls
    ]
    assert methods_and_paths == [
        ("POST", "/librarians/skill-acquisition-jobs"),
        ("GET", "/librarians/skill-acquisition-jobs/job%2F1"),
        ("GET", "/librarians/skill-acquisition-jobs/job%2F1"),
    ]
    assert start_response["status"] == "ACCEPTED"
    assert "secret" not in start_response
    assert "token" not in start_response
    assert status_pending["status"] == "ACCEPTED"
    assert status_pending["result_available"] is False
    assert status_pending.get("skill_id") is None
    assert status_pending.get("context_id") is None
    assert status_complete["status"] == "COMPLETED"
    assert status_complete["result_available"] is True
    assert status_complete["skill_id"] is None
    assert status_complete["context_id"] is None
    assert "secret" not in status_complete
    assert "token" not in status_complete


def test_mcp_path_parameters_are_percent_encoded() -> None:
    """MCP path arguments should remain a single backend path segment."""
    client, calls = _client()

    async def run_tools() -> None:
        await alexandria_archive_context(client, "ctx/1?archive=false")
        await alexandria_get_memory_compact(client, "compact/1#anchor")
        await alexandria_librarian_job_status(client, "job/1")

    anyio.run(run_tools)

    paths = [str(request.url).removeprefix("http://backend:8000") for request in calls]
    assert paths == [
        "/memory/contexts/ctx%2F1%3Farchive%3Dfalse/archive",
        "/memory/compacts/compact%2F1%23anchor",
        "/librarians/jobs/job%2F1",
    ]


def test_mcp_memory_compact_tools_map_to_selected_artifact_endpoints() -> None:
    """Memory Compact MCP tools should use first-class compact endpoints."""
    client, calls = _client()

    async def run_tools() -> None:
        await alexandria_list_memory_compact_artifacts(
            client,
            project="alexandria-hermes",
            status=MemoryCompactStatus.CURRENT,
            limit=3,
        )
        await alexandria_get_current_memory_compact(client, project="alexandria-hermes")
        await alexandria_get_memory_compact(client, "compact/1")
        await alexandria_delete_memory_compact(client, "compact/1")

    anyio.run(run_tools)

    methods_and_paths = [
        (request.method, str(request.url).removeprefix("http://backend:8000"))
        for request in calls
    ]
    assert methods_and_paths == [
        (
            "GET",
            "/memory/compacts?limit=3&offset=0&project=alexandria-hermes&status=CURRENT",
        ),
        ("GET", "/memory/compacts/current?project=alexandria-hermes"),
        ("GET", "/memory/compacts/compact%2F1"),
        ("DELETE", "/memory/compacts/compact%2F1"),
    ]


def test_mcp_obsidian_tools_map_to_vault_endpoints() -> None:
    """Obsidian MCP tools should call the vault API wrappers."""
    client, calls = _client()

    async def run_tools() -> None:
        await alexandria_reindex_vault(client)
        await alexandria_search_vault(
            client,
            query="canonical markdown",
            limit=2,
            alexandria_type="context",
            project="alexandria-hermes",
            tags=["obsidian"],
        )
        await alexandria_read_note(client, path="Alexandria/START_HERE.md")
        await alexandria_get_related_notes(
            client, path="Alexandria/START_HERE.md", limit=2
        )
        await alexandria_save_note(
            client,
            title="Web Research",
            body="# Skill",
            alexandria_type="skill",
            note_id="skill_web_research",
            tags=["research"],
        )
        await alexandria_ask_obsidian_librarian(
            client,
            query="canonical storage",
            active_note_path="Alexandria/START_HERE.md",
            save_transcript=True,
            delegate_to_librarian=True,
            provider_id="codex-oauth",
            profile_id="research-critic",
        )

    anyio.run(run_tools)

    methods_and_paths = [
        (request.method, str(request.url).removeprefix("http://backend:8000"))
        for request in calls
    ]
    search_body = loads_json(calls[1].content or b"{}")
    save_body = loads_json(calls[4].content or b"{}")
    ask_body = loads_json(calls[5].content or b"{}")
    assert methods_and_paths == [
        ("POST", "/obsidian/index/rebuild"),
        ("POST", "/obsidian/search"),
        ("GET", "/obsidian/notes/by-path?path=Alexandria%2FSTART_HERE.md"),
        (
            "GET",
            "/obsidian/notes/by-path/related?path=Alexandria%2FSTART_HERE.md&limit=2",
        ),
        ("POST", "/obsidian/notes"),
        ("POST", "/obsidian/librarian/ask"),
    ]
    assert search_body == {
        "query": "canonical markdown",
        "limit": 2,
        "tags": ["obsidian"],
        "alexandria_type": "context",
        "project": "alexandria-hermes",
    }
    assert save_body["id"] == "skill_web_research"
    assert ask_body["save_transcript"] is True
    assert ask_body["delegate_to_librarian"] is True
    assert ask_body["provider_id"] == "codex-oauth"
    assert ask_body["profile_id"] == "research-critic"


def test_mcp_context_delete_tool_maps_to_hard_delete_endpoint() -> None:
    """Context delete MCP tool should call the hard-delete context endpoint."""
    client, calls = _client()

    _run_json(alexandria_delete_context(client, "ctx/1"))

    assert calls[0].method == "DELETE"
    assert str(calls[0].url) == "http://backend:8000/memory/contexts/ctx%2F1"


def test_mcp_librarian_brief_preview_uses_budgeted_packet_contract() -> None:
    """MCP brief preview should call the compact/source-ref preview endpoint."""
    client, calls = _client()

    _run_json(
        alexandria_librarian_brief_preview(
            client,
            prompt="Need OAuth callback evidence",
            project="alexandria-hermes",
            max_input_chars=3000,
            max_source_refs=4,
        )
    )

    request_body = loads_json(calls[0].content or b"{}")
    assert calls[0].method == "POST"
    assert str(calls[0].url) == "http://backend:8000/librarians/brief-preview"
    assert request_body == {
        "prompt": "Need OAuth callback evidence",
        "project": "alexandria-hermes",
        "budget": {
            "max_input_chars": 3000,
            "max_source_refs": 4,
            "max_preview_chars": 800,
        },
    }


def test_mcp_collaboration_tools_map_to_librarian_backend_contracts() -> None:
    """MCP collaboration tools should call librarian APIs without usage CRUD."""
    client, calls = _client()

    async def run_tools() -> None:
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
    ask_body = loads_json(calls[0].content or b"{}")
    route_preview_body = loads_json(calls[1].content or b"{}")
    assert methods_and_paths == [
        ("POST", "/librarians/ask"),
        ("POST", "/librarians/route-preview"),
        ("GET", "/librarians/jobs/job%2F1"),
    ]
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


def test_fastapi_app_mounts_guarded_streamable_http_mcp_endpoint() -> None:
    """FastAPI should expose the real FastMCP HTTP app behind operator auth."""
    initialize_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "pytest", "version": "0.1.0"},
        },
    }

    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        unauthorized = client.post("/mcp/", json=initialize_request)
        response = client.post(
            "/mcp/",
            json=initialize_request,
            headers={
                OPERATOR_API_KEY_HEADER: "test-operator-api-key-for-route-contracts-000000000000",
                "Accept": "application/json, text/event-stream",
            },
        )

    assert unauthorized.status_code == 401
    assert response.status_code == 200
    assert response.json()["result"]["serverInfo"]["name"] == "Alexandria-Hermes"


def test_fastmcp_server_registers_required_alexandria_tools() -> None:
    """FastMCP registration should expose the durable tool contract names."""
    client, _ = _client()
    server = build_mcp_server(client=client)

    tools = anyio.run(server.list_tools)

    names = {tool.name for tool in tools}
    assert {
        "alexandria_search",
        "alexandria_recall_context",
        "alexandria_rag_context",
        "alexandria_list_memory_compact_artifacts",
        "alexandria_get_current_memory_compact",
        "alexandria_get_memory_compact",
        "alexandria_delete_memory_compact",
        "alexandria_start_skill_acquisition",
        "alexandria_skill_acquisition_job_status",
        "alexandria_complete_skill_acquisition",
        "alexandria_ask_librarian",
        "alexandria_librarian_brief_preview",
        "alexandria_librarian_route_preview",
        "alexandria_librarian_job_status",
        "alexandria_librarian_oauth_start",
        "alexandria_librarian_oauth_poll",
        "alexandria_librarian_oauth_status",
        "alexandria_librarian_oauth_refresh",
        "alexandria_archive_context",
        "alexandria_delete_context",
        "alexandria_rag_status",
        "alexandria_reindex_vault",
        "alexandria_search_vault",
        "alexandria_read_note",
        "alexandria_save_note",
        "alexandria_ask_obsidian_librarian",
    } <= names
    assert {
        "alexandria_get_skill",
        "alexandria_get_prompt",
        "alexandria_search_library",
        "alexandria_search_skills",
        "alexandria_search_prompts",
        "alexandria_capture_harness",
        "alexandria_check_harness",
        "alexandria_list_harnesses",
        "alexandria_get_harness",
        "alexandria_archive_harness",
        "alexandria_submit_skill_candidate",
        "alexandria_record_usage",
        "alexandria_capture_context",
        "alexandria_prepare_compact",
    }.isdisjoint(names)
