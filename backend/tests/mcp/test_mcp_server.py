"""MCP server tests for HTTP-only Alexandria tools."""

from __future__ import annotations

from collections.abc import Awaitable
from inspect import iscoroutinefunction

import anyio
import httpx
from app.main import app
from app.mcp_server.backend_api_client import (
    AlexandriaApiClient,
    AlexandriaApiSettings,
)
from app.mcp_server.backend_tool_gateway import (
    alexandria_archive_context,
    alexandria_archive_memory_compact,
    alexandria_ask_librarian,
    alexandria_ask_obsidian_librarian,
    alexandria_complete_skill_acquisition,
    alexandria_create_memory_compact,
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
    alexandria_librarian_readiness,
    alexandria_librarian_refresh_current_compact,
    alexandria_librarian_review_apply_moves,
    alexandria_librarian_review_move_plan,
    alexandria_librarian_review_queue,
    alexandria_librarian_route_preview,
    alexandria_librarian_vault_apply_moves,
    alexandria_librarian_vault_inventory,
    alexandria_librarian_vault_move_plan,
    alexandria_librarian_vault_path_search,
    alexandria_list_memory_compact_artifacts,
    alexandria_mark_memory_compact_current,
    alexandria_operational_readiness,
    alexandria_rag_status,
    alexandria_read_note,
    alexandria_recovery_plan,
    alexandria_recovery_quarantine,
    alexandria_recovery_retry,
    alexandria_recovery_run,
    alexandria_recovery_run_status,
    alexandria_reindex_vault,
    alexandria_review_memory_compact,
    alexandria_save_note,
    alexandria_search,
    alexandria_search_skills,
    alexandria_search_vault,
    alexandria_skill_acquisition_job_status,
    alexandria_start_skill_acquisition,
)
from app.mcp_server.server_runtime import build_mcp_server
from app.memory.domain.event_enum.context_enums import ContextRecallLifecycleStatus
from app.memory.domain.event_enum.memory_compact_enums import (
    MemoryCompactStatus,
)
from app.memory.interface.schemas.context.context_schema import ContextSearchRequest
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


def _compact_review_payload(
    compact_id: str = "compact-1",
    *,
    verdict: str = "pass",
) -> JSONValue:
    return {
        "compact_id": compact_id,
        "verdict": verdict,
        "total_score": 20 if verdict == "pass" else 12,
        "max_score": 20,
        "scores": [],
        "missing_refs": [],
        "contradictions": [],
        "stale_reasons": [],
        "recommended_actions": (
            ["promote_or_keep_current"]
            if verdict == "pass"
            else ["revise_memory_compact"]
        ),
    }


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
        alexandria_librarian_readiness,
        alexandria_librarian_refresh_current_compact,
        alexandria_operational_readiness,
        alexandria_recovery_plan,
        alexandria_recovery_quarantine,
        alexandria_recovery_retry,
        alexandria_recovery_run,
        alexandria_recovery_run_status,
        alexandria_librarian_review_queue,
        alexandria_librarian_review_move_plan,
        alexandria_librarian_review_apply_moves,
        alexandria_librarian_vault_inventory,
        alexandria_librarian_vault_path_search,
        alexandria_librarian_vault_move_plan,
        alexandria_librarian_vault_apply_moves,
        alexandria_ask_obsidian_librarian,
        alexandria_list_memory_compact_artifacts,
        alexandria_search_skills,
        alexandria_start_skill_acquisition,
        alexandria_save_note,
        alexandria_skill_acquisition_job_status,
        alexandria_complete_skill_acquisition,
        alexandria_get_current_memory_compact,
        alexandria_create_memory_compact,
        alexandria_get_memory_compact,
        alexandria_mark_memory_compact_current,
        alexandria_archive_memory_compact,
        alexandria_review_memory_compact,
        alexandria_delete_memory_compact,
    ]

    assert all(iscoroutinefunction(tool) for tool in async_tools)


def test_mcp_client_sends_backend_http_without_custom_auth_headers() -> None:
    """MCP client should call the backend URL without custom auth headers."""
    client, calls = _client()

    payload = _run_json(
        alexandria_search(
            client,
            ContextSearchRequest(query="context recall", limit=3, strategy="FTS_ONLY"),
        )
    )

    request = calls[0]
    request_body = loads_json(request.content or b"{}")
    assert payload == {"ok": True}
    assert request.method == "POST"
    assert str(request.url) == "http://backend:8000/memory/contexts/retrieval/search"
    assert request.headers["accept"] == "application/json"
    assert request.headers["content-type"] == "application/json"
    assert "authorization" not in request.headers
    assert "x-alexandria-operator-key" not in request.headers
    assert request_body == {
        "query": "context recall",
        "strategy": "FTS_ONLY",
        "limit": 3,
    }


def test_mcp_search_forwards_explicit_lifecycle_statuses() -> None:
    client, calls = _client()

    _run_json(
        alexandria_search(
            client,
            ContextSearchRequest(
                query="administrative recall",
                include_lifecycle_statuses=[
                    ContextRecallLifecycleStatus.SUPERSEDED,
                    ContextRecallLifecycleStatus.ARCHIVED,
                ],
            ),
        )
    )

    request_body = loads_json(calls[0].content or b"{}")
    assert request_body == {
        "query": "administrative recall",
        "strategy": "HYBRID",
        "limit": 5,
        "include_lifecycle_statuses": ["SUPERSEDED", "ARCHIVED"],
    }


def test_mcp_search_skills_maps_to_search_first_endpoint() -> None:
    """MCP search-first skill tool should call the dedicated librarian endpoint."""
    client, calls = _client()

    payload = _run_json(
        alexandria_search_skills(
            client,
            capability="browser automation",
            task_goal="Run deterministic browser checks",
            project="alexandria-hermes",
            environment="pytest",
            required_tools=["playwright"],
            success_criteria=["stable selectors"],
            limit=3,
        )
    )

    request = calls[0]
    body = loads_json(request.content or b"{}")
    assert payload == {"ok": True}
    assert request.method == "POST"
    assert str(request.url) == "http://backend:8000/librarians/skill-library/search"
    assert body == {
        "capability": "browser automation",
        "task_goal": "Run deterministic browser checks",
        "project": "alexandria-hermes",
        "environment": "pytest",
        "required_tools": ["playwright"],
        "constraints": [],
        "risk_tolerance": "MEDIUM",
        "success_criteria": ["stable selectors"],
        "limit": 3,
    }


def test_mcp_search_skills_preserves_search_first_decision_payload() -> None:
    """MCP skill search should expose sufficiency evidence and repair handoff."""
    response_payload: JSONValue = {
        "decision": "SEARCH_UNAVAILABLE",
        "query": "browser automation playwright stable selectors",
        "candidates": [],
        "recommended_action": "Repair search before starting acquisition.",
        "gaps": ["Skill library search failed"],
        "decision_explanation": {
            "candidate_count": 0,
            "candidate_ids": [],
            "scores": [],
            "hard_gates": {},
            "match_reasons": {},
            "gaps": ["Skill library search failed"],
            "limitations": ["Skill library search unavailable: disk I/O error"],
        },
        "handoff": {
            "decision": "skill_search_repair_required",
            "repair": {
                "tools": [
                    "alexandria_librarian_readiness",
                    "alexandria_reindex_vault",
                ],
                "error": "disk I/O error",
            },
        },
        "search_error": "disk I/O error",
        "token": "backend-secret-token",
    }
    client, calls = _client_with_payload(response_payload)

    payload = _run_json(
        alexandria_search_skills(
            client,
            capability="browser automation",
            task_goal="Run deterministic browser checks",
            required_tools=["playwright"],
            success_criteria=["stable selectors"],
        )
    )

    assert calls[0].method == "POST"
    assert str(calls[0].url) == "http://backend:8000/librarians/skill-library/search"
    assert payload == {
        "decision": "SEARCH_UNAVAILABLE",
        "query": "browser automation playwright stable selectors",
        "candidates": [],
        "recommended_action": "Repair search before starting acquisition.",
        "gaps": ["Skill library search failed"],
        "decision_explanation": {
            "candidate_count": 0,
            "candidate_ids": [],
            "scores": [],
            "hard_gates": {},
            "match_reasons": {},
            "gaps": ["Skill library search failed"],
            "limitations": ["Skill library search unavailable: disk I/O error"],
        },
        "handoff": {
            "decision": "skill_search_repair_required",
            "repair": {
                "tools": [
                    "alexandria_librarian_readiness",
                    "alexandria_reindex_vault",
                ],
                "error": "disk I/O error",
            },
        },
        "search_error": "disk I/O error",
    }


def test_mcp_tools_map_to_non_destructive_backend_endpoints() -> None:
    """MCP tools should expose status/archive without deleted CRUD calls."""
    client, calls = _client()

    async def run_tools() -> None:
        await alexandria_archive_context(client, "ctx-1")
        await alexandria_rag_status(client)
        await alexandria_operational_readiness(client)
        await alexandria_recovery_plan(
            client,
            trigger="manual",
            actor="pytest",
            idempotency_key="mcp-plan-key",
        )
        await alexandria_recovery_run(
            client,
            trigger="manual",
            actor="pytest",
            idempotency_key="mcp-run-key",
        )
        await alexandria_recovery_run_status(client, "run/1")
        await alexandria_recovery_retry(
            client,
            "run/1",
            actor="pytest",
            idempotency_key="mcp-retry-key",
        )
        await alexandria_recovery_quarantine(client)

    anyio.run(run_tools)

    methods_and_paths = [
        (request.method, str(request.url).removeprefix("http://backend:8000"))
        for request in calls
    ]
    assert methods_and_paths == [
        ("POST", "/memory/contexts/ctx-1/archive"),
        ("GET", "/memory/contexts/rag/status"),
        ("GET", "/operations/readiness"),
        ("POST", "/operations/recovery/plan"),
        ("POST", "/operations/recovery/runs"),
        ("GET", "/operations/recovery/runs/run%2F1"),
        ("POST", "/operations/recovery/runs/run%2F1/retry"),
        ("GET", "/operations/recovery/quarantine"),
    ]
    recovery_body = loads_json(calls[3].content or b"{}")
    assert recovery_body == {
        "trigger": "manual",
        "actor": "pytest",
        "idempotency_key": "mcp-plan-key",
    }
    recovery_run_body = loads_json(calls[4].content or b"{}")
    assert recovery_run_body == {
        "trigger": "manual",
        "actor": "pytest",
        "idempotency_key": "mcp-run-key",
    }
    retry_body = loads_json(calls[6].content or b"{}")
    assert retry_body == {
        "trigger": "retry",
        "actor": "pytest",
        "idempotency_key": "mcp-retry-key",
    }
    assert all(method != "DELETE" for method, _ in methods_and_paths)


def test_mcp_recovery_run_requires_explicit_idempotency_key() -> None:
    """MCP recovery apply should fail closed before backend calls without a key."""
    client, calls = _client()

    async def run_tool() -> None:
        await alexandria_recovery_run(client, idempotency_key=None)

    try:
        anyio.run(run_tool)
    except ValueError as exc:
        error_message = str(exc)
    else:  # pragma: no cover - failure path for the guard assertion
        raise AssertionError("alexandria_recovery_run accepted a missing key")

    assert error_message == "idempotency_key is required for alexandria_recovery_run"
    assert calls == []


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
            search_snapshot={
                "decision": "NOT_FOUND",
                "gaps": ["No matching browser automation skill."],
            },
        )
        await alexandria_skill_acquisition_job_status(client, "job/1")
        await alexandria_complete_skill_acquisition(
            client,
            job_id="job/1",
            title="Browser automation skill",
            purpose="Automate browser checks safely.",
            content="Use stable selectors and bounded waits.",
            evidence_urls=["https://example.com/browser"],
            evidence_items=[
                {
                    "url_or_path": "https://example.com/browser",
                    "title": "Browser automation reference",
                    "source_kind": "documentation",
                    "supports_claims": ["Stable selectors reduce flake risk."],
                    "freshness": "current",
                }
            ],
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
        "search_snapshot": {
            "decision": "NOT_FOUND",
            "gaps": ["No matching browser automation skill."],
        },
    }
    assert completion_body["title"] == "Browser automation skill"
    assert completion_body["evidence_urls"] == ["https://example.com/browser"]
    assert completion_body["evidence_items"] == [
        {
            "url_or_path": "https://example.com/browser",
            "title": "Browser automation reference",
            "source_kind": "documentation",
            "supports_claims": ["Stable selectors reduce flake risk."],
            "freshness": "current",
        }
    ]
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
        await alexandria_create_memory_compact(
            client,
            covered_from="2026-07-01T00:00:00Z",
            covered_to="2026-07-15T00:00:00Z",
            markdown_body=(
                "## Durable Decisions\n"
                "- Current compact decision.\n\n"
                "## Current State\n"
                "- Current compact state.\n\n"
                "## Risks and Blockers\n"
                "- None recorded.\n\n"
                "## Next Actions\n"
                "- Continue validation.\n\n"
                "## Coverage\n"
                "- covered_from: 2026-07-01T00:00:00Z\n"
                "- covered_to: 2026-07-15T00:00:00Z\n"
                "- project: alexandria-hermes\n\n"
                "## Evidence Summary\n"
                "- Source note."
            ),
            project="alexandria-hermes",
            status=MemoryCompactStatus.CURRENT,
            source_refs=[
                {
                    "source_type": "obsidian_note",
                    "source_id": "note-1",
                    "title": "Source note",
                    "detail_path": "/obsidian/notes/note-1",
                    "source_hash": "hash-before",
                }
            ],
        )
        await alexandria_get_memory_compact(client, "compact/1")
        await alexandria_review_memory_compact(
            client,
            "compact/1",
            source_observations=[
                {
                    "source_id": "note-1",
                    "detail_path": "/obsidian/notes/note-1",
                    "current_source_hash": "hash-after",
                }
            ],
        )
        await alexandria_mark_memory_compact_current(client, "compact/1")
        await alexandria_archive_memory_compact(client, "compact/1")
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
        ("POST", "/memory/compacts"),
        ("GET", "/memory/compacts/compact%2F1"),
        ("POST", "/memory/compacts/compact%2F1/review"),
        ("POST", "/memory/compacts/compact%2F1/mark-current"),
        ("POST", "/memory/compacts/compact%2F1/archive"),
        ("DELETE", "/memory/compacts/compact%2F1"),
    ]
    create_body = loads_json(calls[2].content or b"{}")
    assert create_body == {
        "covered_from": "2026-07-01T00:00:00Z",
        "covered_to": "2026-07-15T00:00:00Z",
        "markdown_body": (
            "## Durable Decisions\n"
            "- Current compact decision.\n\n"
            "## Current State\n"
            "- Current compact state.\n\n"
            "## Risks and Blockers\n"
            "- None recorded.\n\n"
            "## Next Actions\n"
            "- Continue validation.\n\n"
            "## Coverage\n"
            "- covered_from: 2026-07-01T00:00:00Z\n"
            "- covered_to: 2026-07-15T00:00:00Z\n"
            "- project: alexandria-hermes\n\n"
            "## Evidence Summary\n"
            "- Source note."
        ),
        "project": "alexandria-hermes",
        "status": "CURRENT",
        "source_refs": [
            {
                "source_type": "obsidian_note",
                "source_id": "note-1",
                "title": "Source note",
                "detail_path": "/obsidian/notes/note-1",
                "source_hash": "hash-before",
            }
        ],
    }
    review_body = loads_json(calls[4].content or b"{}")
    assert review_body == {
        "source_observations": [
            {
                "source_id": "note-1",
                "detail_path": "/obsidian/notes/note-1",
                "current_source_hash": "hash-after",
            }
        ]
    }


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
        await alexandria_librarian_review_queue(
            client,
            project="alexandria-hermes",
            scope_path="Alexandria/_Inbox",
            limit=3,
        )
        await alexandria_librarian_review_move_plan(
            client,
            project="alexandria-hermes",
            scope_path="Alexandria/_Inbox",
            limit=3,
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
    queue_body = loads_json(calls[2].content or b"{}")
    move_plan_body = loads_json(calls[3].content or b"{}")
    save_body = loads_json(calls[6].content or b"{}")
    ask_body = loads_json(calls[7].content or b"{}")
    assert methods_and_paths == [
        ("POST", "/obsidian/index/rebuild"),
        ("POST", "/obsidian/search"),
        ("POST", "/obsidian/librarian/review-queue"),
        ("POST", "/obsidian/librarian/review-queue/move-plan"),
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
    assert queue_body == {
        "limit": 3,
        "project": "alexandria-hermes",
        "scope_path": "Alexandria/_Inbox",
    }
    assert move_plan_body == queue_body
    assert save_body["id"] == "skill_web_research"
    assert ask_body["save_transcript"] is True
    assert ask_body["delegate_to_librarian"] is True
    assert ask_body["provider_id"] == "codex-oauth"
    assert ask_body["profile_id"] == "research-critic"


def test_mcp_librarian_review_apply_requires_confirmation_when_plan_has_moves() -> None:
    """Review apply gateway should fail closed before mutating planned moves."""
    calls: list[RecordedCall] = []
    move_plan: JSONValue = {
        "status": "ready",
        "hard_delete_performed": False,
        "moves": [
            {
                "source_path": "Alexandria/_Inbox/Captures/Captured.md",
                "destination_path": "Alexandria/Contexts/Projects/Captured.md",
            }
        ],
        "skipped": [],
        "ambiguous": [],
    }

    async def fake_transport(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, content=dumps_json(move_plan))

    client = AlexandriaApiClient(
        AlexandriaApiSettings(
            base_url="http://backend:8000",
            timeout=12.0,
        ),
        transport=httpx.MockTransport(fake_transport),
    )

    payload = _run_json(
        alexandria_librarian_review_apply_moves(
            client,
            project="alexandria-hermes",
            scope_path="Alexandria/_Inbox",
            limit=3,
        )
    )

    assert [
        (request.method, str(request.url).removeprefix("http://backend:8000"))
        for request in calls
    ] == [("POST", "/obsidian/librarian/review-queue/move-plan")]
    assert payload == {
        "status": "confirmation_required",
        "hard_delete_performed": False,
        "moved": [],
        "skipped": [],
        "ambiguous": [],
        "apply_skipped_reason": "confirm_apply_required",
        "move_plan": move_plan,
    }


def test_mcp_librarian_review_apply_confirmed_calls_apply_endpoint() -> None:
    """Confirmed review apply should plan first and then call the apply endpoint."""
    calls: list[RecordedCall] = []
    responses: list[JSONValue] = [
        {
            "status": "ready",
            "hard_delete_performed": False,
            "moves": [
                {
                    "source_path": "Alexandria/_Inbox/Captures/Captured.md",
                    "destination_path": "Alexandria/Contexts/Projects/Captured.md",
                }
            ],
            "skipped": [],
            "ambiguous": [],
        },
        {
            "status": "applied",
            "hard_delete_performed": False,
            "moved": [
                {
                    "source_path": "Alexandria/_Inbox/Captures/Captured.md",
                    "destination_path": "Alexandria/Contexts/Projects/Captured.md",
                }
            ],
        },
    ]

    async def fake_transport(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, content=dumps_json(responses[len(calls) - 1]))

    client = AlexandriaApiClient(
        AlexandriaApiSettings(
            base_url="http://backend:8000",
            timeout=12.0,
        ),
        transport=httpx.MockTransport(fake_transport),
    )

    payload = _run_json(
        alexandria_librarian_review_apply_moves(
            client,
            project="alexandria-hermes",
            scope_path="Alexandria/_Inbox",
            limit=3,
            report_path="Alexandria/_Ops/Librarian/Reports/review-apply",
            verification_query="canonical markdown",
            confirm_apply=True,
        )
    )

    methods_and_paths = [
        (request.method, str(request.url).removeprefix("http://backend:8000"))
        for request in calls
    ]
    apply_body = loads_json(calls[1].content or b"{}")
    assert methods_and_paths == [
        ("POST", "/obsidian/librarian/review-queue/move-plan"),
        ("POST", "/obsidian/librarian/review-queue/apply-moves"),
    ]
    assert apply_body == {
        "limit": 3,
        "reindex": True,
        "project": "alexandria-hermes",
        "scope_path": "Alexandria/_Inbox",
        "report_path": "Alexandria/_Ops/Librarian/Reports/review-apply",
        "verification_query": "canonical markdown",
    }
    assert payload["status"] == "applied"


def test_mcp_librarian_readiness_combines_health_compact_and_review_queue() -> None:
    """Readiness should summarize second-brain health in one MCP response."""
    calls: list[RecordedCall] = []
    responses: list[JSONValue] = [
        {
            "fts": "HEALTHY",
            "vector": "HEALTHY",
            "embedding": "HEALTHY",
            "default_strategy": "HYBRID",
            "warnings": [],
        },
        {
            "id": "compact-1",
            "project": "alexandria-hermes",
            "status": "CURRENT",
            "updated_at": "2026-07-15T00:00:00Z",
        },
        {"items": [], "total": 0},
        _compact_review_payload("compact-old"),
        _compact_review_payload("compact-1"),
    ]

    async def fake_transport(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, content=dumps_json(responses[len(calls) - 1]))

    client = AlexandriaApiClient(
        AlexandriaApiSettings(
            base_url="http://backend:8000",
            timeout=12.0,
        ),
        transport=httpx.MockTransport(fake_transport),
    )

    payload = _run_json(
        alexandria_librarian_readiness(
            client, project="alexandria-hermes", max_compact_age_days=365_000
        )
    )

    methods_and_paths = [
        (request.method, str(request.url).removeprefix("http://backend:8000"))
        for request in calls
    ]
    review_queue_body = loads_json(calls[2].content or b"{}")
    assert methods_and_paths == [
        ("GET", "/memory/contexts/rag/status"),
        ("GET", "/memory/compacts/current?project=alexandria-hermes"),
        ("POST", "/obsidian/librarian/review-queue"),
        ("POST", "/memory/compacts/compact-1/review"),
    ]
    assert review_queue_body == {"limit": 20, "project": "alexandria-hermes"}
    assert payload["ready"] is True
    assert payload["status"] == "ready"
    assert payload["current_memory_compact"]["id"] == "compact-1"
    assert payload["current_memory_compact"]["max_age_days"] == 365_000
    assert payload["review_queue"]["total"] == 0
    assert payload["review_queue"]["auto_move_candidates"] == 0
    assert payload["review_queue"]["manual_review_required"] == 0
    assert payload["current_memory_compact_review"]["verdict"] == "pass"
    assert payload["warnings"] == []
    assert payload["next_actions"] == []


def test_mcp_librarian_readiness_flags_stale_current_compact() -> None:
    """Readiness should fail closed when the current compact is too old."""
    calls: list[RecordedCall] = []
    responses: list[JSONValue] = [
        {"fts": "HEALTHY", "vector": "HEALTHY", "embedding": "HEALTHY"},
        {
            "id": "compact-old",
            "project": "alexandria-hermes",
            "status": "CURRENT",
            "updated_at": "2000-01-01T00:00:00Z",
        },
        {"items": [], "total": 0},
        _compact_review_payload("compact-old"),
        _compact_review_payload("compact-old"),
        _compact_review_payload("compact-old"),
    ]

    async def fake_transport(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, content=dumps_json(responses[len(calls) - 1]))

    client = AlexandriaApiClient(
        AlexandriaApiSettings(
            base_url="http://backend:8000",
            timeout=12.0,
        ),
        transport=httpx.MockTransport(fake_transport),
    )

    payload = _run_json(
        alexandria_librarian_readiness(
            client, project="alexandria-hermes", max_compact_age_days=30
        )
    )

    assert payload["ready"] is False
    assert payload["status"] == "needs_attention"
    assert payload["current_memory_compact"]["id"] == "compact-old"
    assert payload["current_memory_compact"]["max_age_days"] == 30
    assert payload["current_memory_compact"]["age_days"] > 30
    assert payload["warnings"] == ["current_memory_compact_stale"]
    assert payload["next_actions"] == [
        {
            "priority": 20,
            "code": "refresh_current_memory_compact",
            "tool": "alexandria_librarian_refresh_current_compact",
            "summary": "Refresh the CURRENT Memory Compact from readiness evidence.",
            "dry_run_first": True,
        }
    ]


def test_mcp_librarian_readiness_flags_missing_current_compact_timestamp() -> None:
    """Readiness should preserve missing timestamp warnings from compact API."""
    calls: list[RecordedCall] = []
    responses: list[JSONValue] = [
        {"fts": "HEALTHY", "vector": "HEALTHY", "embedding": "HEALTHY"},
        {
            "id": "compact-missing-timestamp",
            "project": "alexandria-hermes",
            "status": "CURRENT",
            "updated_at": "2026-07-17T00:00:00Z",
            "warnings": ["memory_compact_timestamp_missing"],
        },
        {"items": [], "total": 0},
        _compact_review_payload("compact-missing-timestamp"),
    ]

    async def fake_transport(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, content=dumps_json(responses[len(calls) - 1]))

    client = AlexandriaApiClient(
        AlexandriaApiSettings(
            base_url="http://backend:8000",
            timeout=12.0,
        ),
        transport=httpx.MockTransport(fake_transport),
    )

    payload = _run_json(
        alexandria_librarian_readiness(
            client, project="alexandria-hermes", max_compact_age_days=365_000
        )
    )

    assert payload["ready"] is False
    assert payload["status"] == "needs_attention"
    assert payload["current_memory_compact"]["id"] == "compact-missing-timestamp"
    assert payload["warnings"] == ["current_memory_compact_timestamp_missing"]
    assert payload["next_actions"] == [
        {
            "priority": 20,
            "code": "refresh_current_memory_compact",
            "tool": "alexandria_librarian_refresh_current_compact",
            "summary": "Refresh the CURRENT Memory Compact from readiness evidence.",
            "dry_run_first": True,
        }
    ]


def test_mcp_librarian_readiness_flags_source_hash_changed_current_compact() -> None:
    """Readiness should mark CURRENT stale when source evidence hash changed."""
    calls: list[RecordedCall] = []
    responses: list[JSONValue] = [
        {"fts": "HEALTHY", "vector": "HEALTHY", "embedding": "HEALTHY"},
        {
            "id": "compact-source-changed",
            "project": "alexandria-hermes",
            "status": "CURRENT",
            "updated_at": "2999-01-01T00:00:00Z",
            "source_refs": [
                {
                    "source_type": "CONTEXT",
                    "source_id": "ctx-1",
                    "title": "Decision source",
                    "detail_path": "/memory/contexts/ctx-1",
                    "source_hash": "hash-before",
                    "current_source_hash": "hash-after",
                }
            ],
        },
        {"items": [], "total": 0},
        _compact_review_payload("compact-source-changed"),
    ]

    async def fake_transport(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, content=dumps_json(responses[len(calls) - 1]))

    client = AlexandriaApiClient(
        AlexandriaApiSettings(
            base_url="http://backend:8000",
            timeout=12.0,
        ),
        transport=httpx.MockTransport(fake_transport),
    )

    payload = _run_json(
        alexandria_librarian_readiness(
            client, project="alexandria-hermes", max_compact_age_days=30
        )
    )

    assert payload["ready"] is False
    assert payload["warnings"] == ["current_memory_compact_stale"]
    assert (
        payload["current_memory_compact"]["source_refs"][0]["source_hash"]
        == "hash-before"
    )
    assert (
        payload["current_memory_compact"]["source_refs"][0]["current_source_hash"]
        == "hash-after"
    )


def test_mcp_librarian_readiness_flags_blocked_current_compact_review() -> None:
    """Readiness should surface the latest CURRENT compact review verdict."""
    calls: list[RecordedCall] = []
    responses: list[JSONValue] = [
        {"fts": "HEALTHY", "vector": "HEALTHY", "embedding": "HEALTHY"},
        {
            "id": "compact-blocked",
            "project": "alexandria-hermes",
            "status": "CURRENT",
            "updated_at": "2999-01-01T00:00:00Z",
        },
        {"items": [], "total": 0},
        _compact_review_payload("compact-blocked", verdict="blocked"),
    ]

    async def fake_transport(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, content=dumps_json(responses[len(calls) - 1]))

    client = AlexandriaApiClient(
        AlexandriaApiSettings(
            base_url="http://backend:8000",
            timeout=12.0,
        ),
        transport=httpx.MockTransport(fake_transport),
    )

    payload = _run_json(
        alexandria_librarian_readiness(
            client, project="alexandria-hermes", max_compact_age_days=30
        )
    )

    methods_and_paths = [
        (request.method, str(request.url).removeprefix("http://backend:8000"))
        for request in calls
    ]
    assert methods_and_paths == [
        ("GET", "/memory/contexts/rag/status"),
        ("GET", "/memory/compacts/current?project=alexandria-hermes"),
        ("POST", "/obsidian/librarian/review-queue"),
        ("POST", "/memory/compacts/compact-blocked/review"),
    ]
    assert payload["ready"] is False
    assert payload["current_memory_compact_review"]["verdict"] == "blocked"
    assert payload["warnings"] == ["current_memory_compact_review_blocked"]
    assert payload["next_actions"] == [
        {
            "priority": 20,
            "code": "refresh_current_memory_compact",
            "tool": "alexandria_librarian_refresh_current_compact",
            "summary": "Refresh the CURRENT Memory Compact from readiness evidence.",
            "dry_run_first": True,
        }
    ]


def test_mcp_librarian_readiness_returns_blocked_payload_when_rag_status_fails() -> (
    None
):
    """Readiness should fail closed when RAG status cannot be loaded."""
    calls: list[RecordedCall] = []

    async def fake_transport(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(503, content=dumps_json({"detail": "rag unavailable"}))

    client = AlexandriaApiClient(
        AlexandriaApiSettings(
            base_url="http://backend:8000",
            timeout=12.0,
        ),
        transport=httpx.MockTransport(fake_transport),
    )

    payload = _run_json(
        alexandria_librarian_readiness(
            client, project="alexandria-hermes", max_compact_age_days=30
        )
    )

    paths = [str(request.url).removeprefix("http://backend:8000") for request in calls]
    assert paths == ["/memory/contexts/rag/status"]
    assert payload["ready"] is False
    assert payload["status"] == "needs_attention"
    assert payload["warnings"] == ["rag_status_unavailable"]
    assert payload["rag"]["warnings"] == ["HTTP 503: rag unavailable"]
    assert payload["next_actions"] == [
        {
            "priority": 10,
            "code": "repair_rag_index",
            "tool": "alexandria_reindex_vault",
            "summary": "Repair or rebuild retrieval indexes before trusting answers.",
            "dry_run_first": False,
        }
    ]


def test_mcp_librarian_readiness_flags_attention_items() -> None:
    """Readiness should surface degraded RAG, missing compact, and queue backlog."""
    calls: list[RecordedCall] = []
    responses: list[JSONValue] = [
        {"fts": "HEALTHY", "vector": "REINDEX_REQUIRED", "embedding": "HEALTHY"},
        {},
        {
            "items": [
                {
                    "id": "draft-1",
                    "suggested_destination_path": "Alexandria/Skills/Active/Draft.md",
                    "requires_human_review": True,
                },
                {
                    "id": "inbox-1",
                    "suggested_destination_path": (
                        "Alexandria/Contexts/Projects/Inbox.md"
                    ),
                    "requires_human_review": False,
                },
            ],
            "total": 2,
        },
    ]

    async def fake_transport(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, content=dumps_json(responses[len(calls) - 1]))

    client = AlexandriaApiClient(
        AlexandriaApiSettings(
            base_url="http://backend:8000",
            timeout=12.0,
        ),
        transport=httpx.MockTransport(fake_transport),
    )

    payload = _run_json(alexandria_librarian_readiness(client))

    assert payload["ready"] is False
    assert payload["status"] == "needs_attention"
    assert payload["warnings"] == [
        "rag_vector_not_healthy",
        "current_memory_compact_missing",
        "librarian_review_queue_not_empty",
    ]
    assert payload["review_queue"]["total"] == 2
    assert payload["review_queue"]["auto_move_candidates"] == 1
    assert payload["review_queue"]["manual_review_required"] == 1
    assert payload["next_actions"] == [
        {
            "priority": 10,
            "code": "repair_rag_index",
            "tool": "alexandria_reindex_vault",
            "summary": "Repair or rebuild retrieval indexes before trusting answers.",
            "dry_run_first": False,
        },
        {
            "priority": 20,
            "code": "refresh_current_memory_compact",
            "tool": "alexandria_librarian_refresh_current_compact",
            "summary": "Refresh the CURRENT Memory Compact from readiness evidence.",
            "dry_run_first": True,
        },
        {
            "priority": 30,
            "code": "curate_librarian_review_queue",
            "tool": "alexandria_librarian_review_move_plan",
            "summary": "Plan safe vault moves for automatic review candidates.",
            "dry_run_first": True,
        },
        {
            "priority": 40,
            "code": "review_manual_librarian_queue",
            "tool": "alexandria_librarian_review_queue",
            "summary": "Inspect queue items that require human or librarian judgment.",
            "dry_run_first": True,
        },
    ]


def test_mcp_librarian_readiness_separates_manual_review_queue_action() -> None:
    """Manual-only review queues should not recommend an automatic move plan."""
    calls: list[RecordedCall] = []
    responses: list[JSONValue] = [
        {"fts": "HEALTHY", "vector": "HEALTHY", "embedding": "HEALTHY"},
        {
            "id": "compact-1",
            "project": "alexandria-hermes",
            "status": "CURRENT",
            "updated_at": "2999-01-01T00:00:00Z",
        },
        {
            "items": [
                {
                    "id": "skill-draft",
                    "suggested_destination_path": "Alexandria/Skills/Active/Draft.md",
                    "requires_human_review": True,
                }
            ],
            "total": 1,
        },
        _compact_review_payload("compact-1"),
    ]

    async def fake_transport(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, content=dumps_json(responses[len(calls) - 1]))

    client = AlexandriaApiClient(
        AlexandriaApiSettings(
            base_url="http://backend:8000",
            timeout=12.0,
        ),
        transport=httpx.MockTransport(fake_transport),
    )

    payload = _run_json(
        alexandria_librarian_readiness(
            client,
            project="alexandria-hermes",
            max_compact_age_days=365_000,
        )
    )

    assert payload["ready"] is False
    assert payload["warnings"] == ["librarian_review_queue_not_empty"]
    assert payload["review_queue"]["auto_move_candidates"] == 0
    assert payload["review_queue"]["manual_review_required"] == 1
    assert payload["next_actions"] == [
        {
            "priority": 40,
            "code": "review_manual_librarian_queue",
            "tool": "alexandria_librarian_review_queue",
            "summary": "Inspect queue items that require human or librarian judgment.",
            "dry_run_first": True,
        }
    ]


def test_mcp_librarian_refresh_current_compact_plans_stale_compact_refresh() -> None:
    """Refresh tool should draft a CURRENT compact without mutating by default."""
    calls: list[RecordedCall] = []
    responses: list[JSONValue] = [
        {"fts": "HEALTHY", "vector": "HEALTHY", "embedding": "HEALTHY"},
        {
            "id": "compact-old",
            "project": "alexandria-hermes",
            "status": "CURRENT",
            "updated_at": "2000-01-01T00:00:00Z",
        },
        {"items": [], "total": 0},
        _compact_review_payload("compact-old"),
    ]

    async def fake_transport(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, content=dumps_json(responses[len(calls) - 1]))

    client = AlexandriaApiClient(
        AlexandriaApiSettings(
            base_url="http://backend:8000",
            timeout=12.0,
        ),
        transport=httpx.MockTransport(fake_transport),
    )

    payload = _run_json(
        alexandria_librarian_refresh_current_compact(
            client,
            project="alexandria-hermes",
            max_compact_age_days=30,
            apply=False,
            covered_to="2026-07-15T00:00:00Z",
        )
    )

    paths = [str(request.url).removeprefix("http://backend:8000") for request in calls]
    assert paths == [
        "/memory/contexts/rag/status",
        "/memory/compacts/current?project=alexandria-hermes",
        "/obsidian/librarian/review-queue",
        "/memory/compacts/compact-old/review",
    ]
    assert payload["status"] == "refresh_required"
    assert payload["created"] is None
    assert payload["compact_draft"]["covered_from"] == "2000-01-01T00:00:00Z"
    assert payload["compact_draft"]["covered_to"] == "2026-07-15T00:00:00Z"
    assert payload["compact_draft"]["source_refs"][0]["source_id"] == "compact-old"
    assert "current_memory_compact_stale" in payload["readiness"]["warnings"]


def test_mcp_librarian_refresh_current_compact_applies_stale_compact_refresh() -> None:
    """Refresh tool should create a CURRENT compact and re-check readiness when applied."""
    calls: list[RecordedCall] = []
    responses: list[JSONValue] = [
        {"fts": "HEALTHY", "vector": "HEALTHY", "embedding": "HEALTHY"},
        {
            "id": "compact-old",
            "project": "alexandria-hermes",
            "status": "CURRENT",
            "updated_at": "2000-01-01T00:00:00Z",
        },
        {"items": [], "total": 0},
        _compact_review_payload("compact-old"),
        {"id": "compact-new", "project": "alexandria-hermes", "status": "CURRENT"},
        {"fts": "HEALTHY", "vector": "HEALTHY", "embedding": "HEALTHY"},
        {
            "id": "compact-new",
            "project": "alexandria-hermes",
            "status": "CURRENT",
            "updated_at": "2999-01-01T00:00:00Z",
        },
        {"items": [], "total": 0},
        _compact_review_payload("compact-new"),
    ]

    async def fake_transport(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, content=dumps_json(responses[len(calls) - 1]))

    client = AlexandriaApiClient(
        AlexandriaApiSettings(
            base_url="http://backend:8000",
            timeout=12.0,
        ),
        transport=httpx.MockTransport(fake_transport),
    )

    payload = _run_json(
        alexandria_librarian_refresh_current_compact(
            client,
            project="alexandria-hermes",
            max_compact_age_days=30,
            apply=True,
            covered_to="2026-07-15T00:00:00Z",
        )
    )

    methods_and_paths = [
        (request.method, str(request.url).removeprefix("http://backend:8000"))
        for request in calls
    ]
    create_body = loads_json(calls[4].content or b"{}")
    assert methods_and_paths == [
        ("GET", "/memory/contexts/rag/status"),
        ("GET", "/memory/compacts/current?project=alexandria-hermes"),
        ("POST", "/obsidian/librarian/review-queue"),
        ("POST", "/memory/compacts/compact-old/review"),
        ("POST", "/memory/compacts"),
        ("GET", "/memory/contexts/rag/status"),
        ("GET", "/memory/compacts/current?project=alexandria-hermes"),
        ("POST", "/obsidian/librarian/review-queue"),
        ("POST", "/memory/compacts/compact-new/review"),
    ]
    assert create_body["project"] == "alexandria-hermes"
    assert create_body["covered_from"] == "2000-01-01T00:00:00Z"
    assert create_body["covered_to"] == "2026-07-15T00:00:00Z"
    assert create_body["status"] == "CURRENT"
    assert create_body["source_refs"][0]["source_id"] == "compact-old"
    assert payload["status"] == "refreshed"
    assert payload["created"]["id"] == "compact-new"
    assert payload["post_refresh_readiness"]["ready"] is True


def test_mcp_librarian_refresh_current_compact_blocks_apply_when_rag_unhealthy() -> (
    None
):
    """Refresh apply should fail closed on RAG health even when force is requested."""
    calls: list[RecordedCall] = []
    responses: list[JSONValue] = [
        {"fts": "HEALTHY", "vector": "HEALTHY", "embedding": "REINDEX_REQUIRED"},
        {
            "id": "compact-old",
            "project": "alexandria-hermes",
            "status": "CURRENT",
            "updated_at": "2000-01-01T00:00:00Z",
        },
        {"items": [], "total": 0},
        _compact_review_payload("compact-old"),
    ]

    async def fake_transport(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, content=dumps_json(responses[len(calls) - 1]))

    client = AlexandriaApiClient(
        AlexandriaApiSettings(
            base_url="http://backend:8000",
            timeout=12.0,
        ),
        transport=httpx.MockTransport(fake_transport),
    )

    payload = _run_json(
        alexandria_librarian_refresh_current_compact(
            client,
            project="alexandria-hermes",
            max_compact_age_days=30,
            apply=True,
            force=True,
            covered_to="2026-07-15T00:00:00Z",
        )
    )

    methods_and_paths = [
        (request.method, str(request.url).removeprefix("http://backend:8000"))
        for request in calls
    ]
    assert methods_and_paths == [
        ("GET", "/memory/contexts/rag/status"),
        ("GET", "/memory/compacts/current?project=alexandria-hermes"),
        ("POST", "/obsidian/librarian/review-queue"),
        ("POST", "/memory/compacts/compact-old/review"),
    ]
    assert payload["status"] == "blocked_by_rag_health"
    assert payload["created"] is None
    assert payload["blocked_reasons"] == ["rag_embedding_not_healthy"]
    assert payload["blocked_next_actions"] == [
        {
            "priority": 10,
            "code": "repair_rag_index",
            "tool": "alexandria_reindex_vault",
            "summary": "Repair or rebuild retrieval indexes before trusting answers.",
            "dry_run_first": False,
        }
    ]


def test_mcp_librarian_refresh_current_compact_blocks_apply_on_rag_warnings() -> None:
    """Refresh apply should fail closed when RAG status includes warnings."""
    calls: list[RecordedCall] = []
    responses: list[JSONValue] = [
        {
            "fts": "HEALTHY",
            "vector": "HEALTHY",
            "embedding": "HEALTHY",
            "warnings": ["embedding index status check failed: REINDEX_REQUIRED"],
        },
        {
            "id": "compact-old",
            "project": "alexandria-hermes",
            "status": "CURRENT",
            "updated_at": "2000-01-01T00:00:00Z",
        },
        {"items": [], "total": 0},
        _compact_review_payload("compact-old"),
    ]

    async def fake_transport(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, content=dumps_json(responses[len(calls) - 1]))

    client = AlexandriaApiClient(
        AlexandriaApiSettings(
            base_url="http://backend:8000",
            timeout=12.0,
        ),
        transport=httpx.MockTransport(fake_transport),
    )

    payload = _run_json(
        alexandria_librarian_refresh_current_compact(
            client,
            project="alexandria-hermes",
            max_compact_age_days=30,
            apply=True,
            force=True,
            covered_to="2026-07-15T00:00:00Z",
        )
    )

    methods_and_paths = [
        (request.method, str(request.url).removeprefix("http://backend:8000"))
        for request in calls
    ]
    assert methods_and_paths == [
        ("GET", "/memory/contexts/rag/status"),
        ("GET", "/memory/compacts/current?project=alexandria-hermes"),
        ("POST", "/obsidian/librarian/review-queue"),
        ("POST", "/memory/compacts/compact-old/review"),
    ]
    assert payload["status"] == "blocked_by_rag_health"
    assert payload["created"] is None
    assert payload["blocked_reasons"] == ["rag_status_warnings_present"]
    assert "rag_status_warnings_present" in payload["readiness"]["warnings"]
    assert payload["readiness"]["rag"]["warnings"] == [
        "embedding index status check failed: REINDEX_REQUIRED"
    ]


def test_mcp_librarian_refresh_current_compact_blocks_apply_when_rag_status_fails() -> (
    None
):
    """Refresh apply should return a blocked plan when RAG status lookup fails."""
    calls: list[RecordedCall] = []

    async def fake_transport(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(503, content=dumps_json({"detail": "rag unavailable"}))

    client = AlexandriaApiClient(
        AlexandriaApiSettings(
            base_url="http://backend:8000",
            timeout=12.0,
        ),
        transport=httpx.MockTransport(fake_transport),
    )

    payload = _run_json(
        alexandria_librarian_refresh_current_compact(
            client,
            project="alexandria-hermes",
            max_compact_age_days=30,
            apply=True,
            force=True,
            covered_to="2026-07-15T00:00:00Z",
        )
    )

    methods_and_paths = [
        (request.method, str(request.url).removeprefix("http://backend:8000"))
        for request in calls
    ]
    assert methods_and_paths == [("GET", "/memory/contexts/rag/status")]
    assert payload["status"] == "blocked_by_rag_health"
    assert payload["created"] is None
    assert payload["blocked_reasons"] == ["rag_status_unavailable"]
    assert payload["readiness"]["warnings"] == ["rag_status_unavailable"]


def test_mcp_librarian_refresh_current_compact_blocks_apply_for_manual_review() -> None:
    """Refresh apply should not run while librarian review is blocked."""
    calls: list[RecordedCall] = []
    responses: list[JSONValue] = [
        {"fts": "HEALTHY", "vector": "HEALTHY", "embedding": "HEALTHY"},
        {
            "id": "compact-old",
            "project": "alexandria-hermes",
            "status": "CURRENT",
            "updated_at": "2000-01-01T00:00:00Z",
        },
        {
            "items": [
                {
                    "suggested_destination_path": None,
                    "requires_human_review": True,
                }
            ],
            "total": 1,
        },
        _compact_review_payload("compact-old"),
    ]

    async def fake_transport(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, content=dumps_json(responses[len(calls) - 1]))

    client = AlexandriaApiClient(
        AlexandriaApiSettings(
            base_url="http://backend:8000",
            timeout=12.0,
        ),
        transport=httpx.MockTransport(fake_transport),
    )

    payload = _run_json(
        alexandria_librarian_refresh_current_compact(
            client,
            project="alexandria-hermes",
            max_compact_age_days=30,
            apply=True,
            covered_to="2026-07-15T00:00:00Z",
        )
    )

    methods_and_paths = [
        (request.method, str(request.url).removeprefix("http://backend:8000"))
        for request in calls
    ]
    assert methods_and_paths == [
        ("GET", "/memory/contexts/rag/status"),
        ("GET", "/memory/compacts/current?project=alexandria-hermes"),
        ("POST", "/obsidian/librarian/review-queue"),
        ("POST", "/memory/compacts/compact-old/review"),
    ]
    assert payload["status"] == "blocked_by_librarian_review"
    assert payload["created"] is None
    assert payload["blocked_reasons"] == ["librarian_manual_review_required"]
    assert payload["blocked_next_actions"] == [
        {
            "priority": 40,
            "code": "review_manual_librarian_queue",
            "tool": "alexandria_librarian_review_queue",
            "summary": "Inspect queue items that require human or librarian judgment.",
            "dry_run_first": True,
        }
    ]


def test_mcp_librarian_refresh_current_compact_blocks_apply_for_review_verdict() -> (
    None
):
    """Refresh apply should not run when CURRENT compact review is blocked."""
    calls: list[RecordedCall] = []
    responses: list[JSONValue] = [
        {"fts": "HEALTHY", "vector": "HEALTHY", "embedding": "HEALTHY"},
        {
            "id": "compact-blocked",
            "project": "alexandria-hermes",
            "status": "CURRENT",
            "updated_at": "2000-01-01T00:00:00Z",
        },
        {"items": [], "total": 0},
        _compact_review_payload("compact-blocked", verdict="blocked"),
    ]

    async def fake_transport(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, content=dumps_json(responses[len(calls) - 1]))

    client = AlexandriaApiClient(
        AlexandriaApiSettings(
            base_url="http://backend:8000",
            timeout=12.0,
        ),
        transport=httpx.MockTransport(fake_transport),
    )

    payload = _run_json(
        alexandria_librarian_refresh_current_compact(
            client,
            project="alexandria-hermes",
            max_compact_age_days=30,
            apply=True,
            covered_to="2026-07-15T00:00:00Z",
        )
    )

    methods_and_paths = [
        (request.method, str(request.url).removeprefix("http://backend:8000"))
        for request in calls
    ]
    assert methods_and_paths == [
        ("GET", "/memory/contexts/rag/status"),
        ("GET", "/memory/compacts/current?project=alexandria-hermes"),
        ("POST", "/obsidian/librarian/review-queue"),
        ("POST", "/memory/compacts/compact-blocked/review"),
    ]
    assert payload["status"] == "blocked_by_librarian_review"
    assert payload["created"] is None
    assert payload["blocked_reasons"] == ["current_memory_compact_review_blocked"]
    assert payload["blocked_next_actions"] == []


def test_mcp_librarian_vault_operation_tools_map_to_safe_vault_endpoints() -> None:
    """Manual librarian vault operation tools should call typed safe endpoints."""
    client, calls = _client()
    moves = [
        {
            "source_path": "Alexandria/_Inbox/Captures/Loose.md",
            "destination_path": "Alexandria/Contexts/Projects/Loose.md",
            "reason": "classify captured context",
        }
    ]

    async def run_tools() -> None:
        await alexandria_librarian_vault_inventory(
            client, scope_path="Alexandria/_Inbox"
        )
        await alexandria_librarian_vault_path_search(
            client, query="Loose", scope_path="Alexandria/_Inbox"
        )
        await alexandria_librarian_vault_move_plan(client, moves=moves)
        await alexandria_librarian_vault_apply_moves(
            client,
            moves=moves,
            report_path="Alexandria/_Ops/Librarian/Reports/manual-apply",
            verification_query="Loose",
        )

    anyio.run(run_tools)

    methods_and_paths = [
        (request.method, str(request.url).removeprefix("http://backend:8000"))
        for request in calls
    ]
    inventory_body = loads_json(calls[0].content or b"{}")
    path_search_body = loads_json(calls[1].content or b"{}")
    move_plan_body = loads_json(calls[2].content or b"{}")
    apply_body = loads_json(calls[3].content or b"{}")

    assert methods_and_paths == [
        ("POST", "/obsidian/librarian/vault/inventory"),
        ("POST", "/obsidian/librarian/vault/path-search"),
        ("POST", "/obsidian/librarian/vault/move-plan"),
        ("POST", "/obsidian/librarian/vault/apply-moves"),
    ]
    assert inventory_body == {"scope_path": "Alexandria/_Inbox"}
    assert path_search_body == {
        "query": "Loose",
        "scope_path": "Alexandria/_Inbox",
    }
    assert move_plan_body == {"moves": moves}
    assert apply_body == {
        "moves": moves,
        "reindex": True,
        "report_path": "Alexandria/_Ops/Librarian/Reports/manual-apply",
        "verification_query": "Loose",
    }


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


def test_fastapi_app_accepts_tunnel_host_for_streamable_http_mcp() -> None:
    """FastAPI should expose MCP to reverse-tunnel hosts without 421."""
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

    with TestClient(
        app, base_url="https://b973-121-135-181-35.ngrok-free.app"
    ) as client:
        response = client.post(
            "/mcp/",
            json=initialize_request,
            headers={"Accept": "application/json, text/event-stream"},
        )

    assert response.status_code == 200
    assert response.json()["result"]["serverInfo"]["name"] == "Alexandria-Hermes"


def test_fastmcp_server_uses_tunnel_compatible_transport_host() -> None:
    """FastMCP should not install localhost-only Host protection for tunnels."""
    client, _ = _client()
    server = build_mcp_server(client=client)

    assert server.settings.host == "0.0.0.0"
    assert server.settings.transport_security is None


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
        "alexandria_create_memory_compact",
        "alexandria_get_memory_compact",
        "alexandria_review_memory_compact",
        "alexandria_mark_memory_compact_current",
        "alexandria_archive_memory_compact",
        "alexandria_delete_memory_compact",
        "alexandria_search_skills",
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
        "alexandria_librarian_readiness",
        "alexandria_librarian_refresh_current_compact",
        "alexandria_archive_context",
        "alexandria_delete_context",
        "alexandria_rag_status",
        "alexandria_operational_readiness",
        "alexandria_recovery_plan",
        "alexandria_recovery_quarantine",
        "alexandria_recovery_retry",
        "alexandria_recovery_run",
        "alexandria_recovery_run_status",
        "alexandria_reindex_vault",
        "alexandria_search_vault",
        "alexandria_librarian_review_queue",
        "alexandria_librarian_review_move_plan",
        "alexandria_librarian_review_apply_moves",
        "alexandria_librarian_vault_inventory",
        "alexandria_librarian_vault_path_search",
        "alexandria_librarian_vault_move_plan",
        "alexandria_librarian_vault_apply_moves",
        "alexandria_read_note",
        "alexandria_save_note",
        "alexandria_ask_obsidian_librarian",
    } <= names
    assert {
        "alexandria_get_skill",
        "alexandria_get_prompt",
        "alexandria_search_library",
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
