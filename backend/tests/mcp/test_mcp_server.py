"""MCP server tests for HTTP-only Alexandria tools."""

from __future__ import annotations

from collections.abc import Awaitable
from inspect import iscoroutinefunction

import anyio
import httpx
import pytest
from app.library.domain.event_enum.item_enums import ItemType
from app.library.domain.event_enum.prompt_enums import PromptKind
from app.library.domain.event_enum.skill_enums import RiskLevel
from app.mcp_server.backend_api_client import (
    AlexandriaApiClient,
    AlexandriaApiSettings,
)
from app.mcp_server.backend_tool_gateway import (
    alexandria_archive_context,
    alexandria_archive_harness,
    alexandria_ask_librarian,
    alexandria_capture_context,
    alexandria_capture_harness,
    alexandria_check_harness,
    alexandria_complete_skill_acquisition,
    alexandria_get_current_memory_compact,
    alexandria_get_harness,
    alexandria_get_memory_compact,
    alexandria_get_prompt,
    alexandria_get_skill,
    alexandria_librarian_brief_preview,
    alexandria_librarian_job_status,
    alexandria_librarian_oauth_poll,
    alexandria_librarian_oauth_refresh,
    alexandria_librarian_oauth_start,
    alexandria_librarian_oauth_status,
    alexandria_librarian_route_preview,
    alexandria_list_harnesses,
    alexandria_list_memory_compact_artifacts,
    alexandria_rag_status,
    alexandria_record_usage,
    alexandria_search,
    alexandria_search_library,
    alexandria_search_prompts,
    alexandria_search_skills,
    alexandria_skill_acquisition_job_status,
    alexandria_start_skill_acquisition,
    alexandria_submit_skill_candidate,
)
from app.mcp_server.server_runtime import create_mcp_server
from app.memory.domain.event_enum.context_enums import ContextKind
from app.memory.domain.event_enum.memory_compact_enums import (
    MemoryCompactStatus,
)
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
    assert iscoroutinefunction(alexandria_search)
    assert iscoroutinefunction(alexandria_capture_context)
    assert iscoroutinefunction(alexandria_capture_harness)
    assert iscoroutinefunction(alexandria_check_harness)
    assert iscoroutinefunction(alexandria_list_harnesses)
    assert iscoroutinefunction(alexandria_get_harness)
    assert iscoroutinefunction(alexandria_archive_harness)
    assert iscoroutinefunction(alexandria_rag_status)
    assert iscoroutinefunction(alexandria_record_usage)
    assert iscoroutinefunction(alexandria_ask_librarian)
    assert iscoroutinefunction(alexandria_librarian_brief_preview)
    assert iscoroutinefunction(alexandria_librarian_job_status)
    assert iscoroutinefunction(alexandria_librarian_oauth_start)
    assert iscoroutinefunction(alexandria_librarian_oauth_poll)
    assert iscoroutinefunction(alexandria_librarian_oauth_status)
    assert iscoroutinefunction(alexandria_librarian_oauth_refresh)
    assert iscoroutinefunction(alexandria_librarian_route_preview)
    assert iscoroutinefunction(alexandria_list_memory_compact_artifacts)
    assert iscoroutinefunction(alexandria_search_library)
    assert iscoroutinefunction(alexandria_search_skills)
    assert iscoroutinefunction(alexandria_search_prompts)
    assert iscoroutinefunction(alexandria_start_skill_acquisition)
    assert iscoroutinefunction(alexandria_skill_acquisition_job_status)
    assert iscoroutinefunction(alexandria_complete_skill_acquisition)


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


def test_mcp_skill_acquisition_status_polling_returns_durable_handles() -> None:
    """Polling should return job_id/status now and handles after completion."""
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
            "skill_id": "00000000-0000-4000-8000-000000000777",
            "context_id": "00000000-0000-4000-8000-000000000888",
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

    async def run_tools() -> None:
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
    assert status_complete["skill_id"] == "00000000-0000-4000-8000-000000000777"
    assert status_complete["context_id"] == "00000000-0000-4000-8000-000000000888"
    assert "secret" not in status_complete
    assert "token" not in status_complete
    assert (
        "00000000-0000-4000-8000-000000000777" in dumps_json(status_complete).decode()
    )


def test_mcp_capture_marks_agent_authored_context_explicitly() -> None:
    """MCP capture should not rely on implicit backend source-type defaults."""
    client, calls = _client()

    _run_json(
        alexandria_capture_context(client, title="Handoff", content="## Summary\nDone")
    )

    request_body = loads_json(calls[0].content or b"{}")
    assert request_body["source_type"] == "AGENT"


def test_mcp_capture_harness_uses_context_vault_not_library_crud() -> None:
    """Harness MCP capture should target Context Vault's agent-owned route."""
    client, calls = _client()

    _run_json(
        alexandria_capture_harness(
            client,
            task_goal="Remove workflow surface",
            reusable_procedure="Write a pruning contract and remove the public route.",
            project="alexandria-hermes",
            steps=["Add test", "Remove route"],
            commands=["uv run --no-editable pytest -q tests/library"],
            tests=["workflow pruning contract"],
            recall_keywords=["workflow-removal"],
        )
    )

    request_body = loads_json(calls[0].content or b"{}")
    assert calls[0].method == "POST"
    assert str(calls[0].url) == "http://backend:8000/memory/contexts/harnesses/capture"
    assert request_body["task_goal"] == "Remove workflow surface"
    assert request_body["reusable_procedure"] == (
        "Write a pruning contract and remove the public route."
    )
    assert request_body["recall_keywords"] == ["workflow-removal"]


def test_mcp_harness_management_uses_context_vault_routes() -> None:
    """Harness MCP management should wrap the dedicated Context Vault routes."""
    client, calls = _client()

    async def run_tools() -> None:
        await alexandria_check_harness(
            client,
            task_goal="Refactor CLI support",
            reusable_procedure="Read rules, edit, and run make ci.",
            project="alexandria-hermes",
            steps=["Read rules"],
        )
        await alexandria_list_harnesses(
            client,
            project="alexandria-hermes",
            source_agent="Hermes",
            tag="refactor",
            limit=7,
            include_archived=True,
        )
        await alexandria_get_harness(client, "ctx/1")
        await alexandria_archive_harness(client, "ctx/1")

    anyio.run(run_tools)

    methods_and_paths = [
        (call.method, str(call.url).removeprefix("http://backend:8000"))
        for call in calls
    ]
    assert methods_and_paths == [
        ("POST", "/memory/contexts/harnesses/check"),
        (
            "GET",
            "/memory/contexts/harnesses?limit=7&offset=0"
            "&include_archived=true&project=alexandria-hermes"
            "&source_agent=Hermes&tag=refactor",
        ),
        ("GET", "/memory/contexts/harnesses/ctx%2F1"),
        ("POST", "/memory/contexts/harnesses/ctx%2F1/archive"),
    ]
    check_body = loads_json(calls[0].content or b"{}")
    assert check_body["task_goal"] == "Refactor CLI support"
    assert check_body["steps"] == ["Read rules"]


def test_mcp_generic_context_capture_rejects_harness_kind() -> None:
    """Generic context capture must not bypass the HARNESS tool contract."""
    client, calls = _client()

    with pytest.raises(ValueError, match="alexandria_capture_harness"):
        _run_json(
            alexandria_capture_context(
                client,
                title="Spoofed harness",
                content="## Summary\nspoof",
                kind=ContextKind.HARNESS,
            )
        )

    assert calls == []


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


def test_mcp_library_search_tools_use_candidate_endpoint() -> None:
    """Library search MCP tools should not call full item list endpoints."""
    client, calls = _client()

    async def run_tools() -> None:
        await alexandria_search_library(
            client,
            "pytest fixtures",
            item_types=[ItemType.SKILL, ItemType.PROMPT],
            tags=["testing"],
            limit=7,
            offset=2,
        )
        await alexandria_search_skills(
            client,
            "pytest fixtures",
            required_tools=["pytest"],
            risk_level=RiskLevel.LOW,
            tags=["testing"],
            limit=3,
        )
        await alexandria_search_prompts(
            client,
            "review prompt",
            prompt_kind=PromptKind.DEVELOPER,
            tags=["code-review"],
            limit=4,
        )

    anyio.run(run_tools)

    methods_and_paths = [
        (request.method, str(request.url).removeprefix("http://backend:8000"))
        for request in calls
    ]
    assert methods_and_paths == [
        (
            "GET",
            "/library/search?q=pytest+fixtures&item_types=SKILL&item_types=PROMPT"
            "&tags_any=testing&limit=7&offset=2&content_mode=candidate",
        ),
        (
            "GET",
            "/library/search?q=pytest+fixtures&item_type=SKILL"
            "&required_tools=pytest&tags_any=testing&limit=3&offset=0"
            "&content_mode=candidate&risk_level=LOW",
        ),
        (
            "GET",
            "/library/search?q=review+prompt&item_type=PROMPT&tags_any=code-review"
            "&limit=4&offset=0&content_mode=candidate&prompt_kind=DEVELOPER",
        ),
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
    ]


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
    """FastMCP registration should expose the durable tool contract names."""
    client, _ = _client()
    server = create_mcp_server(client=client)

    tools = anyio.run(server.list_tools)

    names = {tool.name for tool in tools}
    assert {
        "alexandria_search",
        "alexandria_get_skill",
        "alexandria_get_prompt",
        "alexandria_search_library",
        "alexandria_search_skills",
        "alexandria_search_prompts",
        "alexandria_recall_context",
        "alexandria_rag_context",
        "alexandria_capture_context",
        "alexandria_capture_harness",
        "alexandria_check_harness",
        "alexandria_list_harnesses",
        "alexandria_get_harness",
        "alexandria_archive_harness",
        "alexandria_list_memory_compact_artifacts",
        "alexandria_get_current_memory_compact",
        "alexandria_get_memory_compact",
        "alexandria_prepare_compact",
        "alexandria_start_skill_acquisition",
        "alexandria_skill_acquisition_job_status",
        "alexandria_complete_skill_acquisition",
        "alexandria_submit_skill_candidate",
        "alexandria_record_usage",
        "alexandria_ask_librarian",
        "alexandria_librarian_brief_preview",
        "alexandria_librarian_route_preview",
        "alexandria_librarian_job_status",
        "alexandria_librarian_oauth_start",
        "alexandria_librarian_oauth_poll",
        "alexandria_librarian_oauth_status",
        "alexandria_librarian_oauth_refresh",
        "alexandria_archive_context",
        "alexandria_rag_status",
    } <= names
    assert "alexandria_request_skill_acquisition" not in names
    assert "alexandria_list_memory_compacts" not in names
