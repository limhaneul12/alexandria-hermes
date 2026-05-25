"""Behavior tests for the Hermes CLI HTTP client."""

from __future__ import annotations

import io
from collections.abc import Callable

import pytest
from app.cli import HttpHeaders, run
from app.cli_support.support.hermes.install.integration_files import (
    alexandria_operating_loop_prompt,
    first_conversation_prompt,
)
from app.shared.serialization.orjson_codec import dumps_json, loads_json

RecordedCall = tuple[str, str, bytes | None, HttpHeaders, float]
TEST_OPERATOR_API_KEY = "test-operator-api-key-for-route-contracts-000000000000"


def _transport(
    response_payload: object,
) -> tuple[Callable[..., tuple[int, bytes]], list[RecordedCall]]:
    calls: list[RecordedCall] = []

    def fake_transport(
        method: str,
        url: str,
        body: bytes | None,
        headers: HttpHeaders,
        timeout: float,
    ) -> tuple[int, bytes]:
        calls.append((method, url, body, headers, timeout))
        response = dumps_json(response_payload)
        return 200, response

    return fake_transport, calls


def test_cli_context_reindex_calls_backend_embedding_reindex() -> None:
    """Context reindex should call the backend embedding backfill endpoint."""
    calls: list[RecordedCall] = []

    def fake_transport(
        method: str,
        url: str,
        body: bytes | None,
        headers: HttpHeaders,
        timeout: float,
    ) -> tuple[int, bytes]:
        calls.append((method, url, body, headers, timeout))
        return 200, dumps_json({"scanned": 2, "updated": 2, "skipped": 0})

    stdout = io.StringIO()

    exit_code = run(
        ["--json", "context", "reindex", "--limit", "250"],
        transport=fake_transport,
        stdout=stdout,
    )

    assert exit_code == 0
    assert calls[0][0] == "POST"
    assert calls[0][1] == (
        "http://localhost:8000/memory/contexts/retrieval/reindex?limit=250&force=false"
    )
    assert loads_json(calls[0][2] or b"{}") == {}
    assert loads_json(stdout.getvalue())["updated"] == 2


def test_cli_context_reindex_can_force_embedding_rebuild() -> None:
    """Context reindex --force should request a full active chunk rebuild."""
    calls: list[RecordedCall] = []

    def fake_transport(
        method: str,
        url: str,
        body: bytes | None,
        headers: HttpHeaders,
        timeout: float,
    ) -> tuple[int, bytes]:
        calls.append((method, url, body, headers, timeout))
        return 200, dumps_json({"scanned": 3, "updated": 3, "skipped": 0})

    stdout = io.StringIO()

    exit_code = run(
        ["--json", "context", "reindex", "--force"],
        transport=fake_transport,
        stdout=stdout,
    )

    assert exit_code == 0
    assert calls[0][0] == "POST"
    assert calls[0][1] == (
        "http://localhost:8000/memory/contexts/retrieval/reindex?limit=100&force=true"
    )
    assert loads_json(calls[0][2] or b"{}") == {}
    assert loads_json(stdout.getvalue())["updated"] == 3


def test_cli_reports_rag_status_and_context_chunks_as_json() -> None:
    """RAG status and chunk inspection remain machine-readable for agents."""
    calls: list[RecordedCall] = []

    def fake_transport(
        method: str,
        url: str,
        body: bytes | None,
        headers: HttpHeaders,
        timeout: float,
    ) -> tuple[int, bytes]:
        calls.append((method, url, body, headers, timeout))
        if url.endswith("/rag/status"):
            return 200, dumps_json({"fts": "HEALTHY", "vector": "DEGRADED"})
        return 200, dumps_json([{"id": "chunk-1", "context_id": "ctx-1"}])

    stdout = io.StringIO()

    status_exit = run(
        ["--json", "context", "doctor-rag"],
        transport=fake_transport,
        stdout=stdout,
    )
    chunks_exit = run(
        ["--json", "context", "chunks", "ctx-1"],
        transport=fake_transport,
        stdout=stdout,
    )

    assert status_exit == 0
    assert chunks_exit == 0
    assert calls[0][1] == "http://localhost:8000/memory/contexts/rag/status"
    assert calls[1][1] == "http://localhost:8000/memory/contexts/ctx-1/chunks"
    assert "chunk-1" in stdout.getvalue()


def test_cli_context_recall_sends_scope_filters_for_memory_routing() -> None:
    """Context recall should forward explicit memory scope filters."""
    transport, calls = _transport({"context_pack": "# Pack", "matches": []})
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "context",
            "recall",
            "install flow",
            "--project",
            "alexandria-hermes",
            "--include",
            "GLOBAL",
            "--include",
            "PROJECT",
            "--include",
            "USER",
            "--user-id",
            "ha_nori",
        ],
        transport=transport,
        stdout=stdout,
    )

    request_body = loads_json((calls[0][2] or b"{}").decode())
    assert exit_code == 0
    assert calls[0][0] == "POST"
    assert calls[0][1] == "http://localhost:8000/memory/contexts/retrieval/search"
    assert request_body == {
        "query": "install flow",
        "strategy": "HYBRID",
        "limit": 5,
        "project": "alexandria-hermes",
        "include_scopes": ["GLOBAL", "PROJECT", "USER"],
        "user_id": "ha_nori",
    }


def test_cli_context_memory_map_and_curate_use_read_routes() -> None:
    """Memory-map and curate should use Context Vault read APIs."""
    calls: list[RecordedCall] = []

    def fake_transport(
        method: str,
        url: str,
        body: bytes | None,
        headers: HttpHeaders,
        timeout: float,
    ) -> tuple[int, bytes]:
        calls.append((method, url, body, headers, timeout))
        return 200, dumps_json(
            {
                "items": [
                    {
                        "id": "ctx-1",
                        "kind": "DECISION",
                        "status": "SAVED_WITH_WARNINGS",
                    }
                ],
                "total": 1,
            }
        )

    stdout = io.StringIO()

    memory_map_exit = run(
        [
            "--json",
            "context",
            "memory-map",
            "--project",
            "alexandria-hermes",
        ],
        transport=fake_transport,
        stdout=stdout,
    )
    curate_exit = run(
        ["--json", "context", "curate", "--project", "alexandria-hermes"],
        transport=fake_transport,
        stdout=stdout,
    )

    assert memory_map_exit == 0
    assert curate_exit == 0
    assert calls[0][1] == (
        "http://localhost:8000/memory/contexts?limit=10&offset=0"
        "&include_archived=false&project=alexandria-hermes"
    )
    assert calls[1][1] == (
        "http://localhost:8000/memory/contexts?limit=50&offset=0"
        "&include_archived=false&project=alexandria-hermes"
    )


def test_hermes_onboard_dry_run_plans_prompts_skill_and_mcp_config(tmp_path) -> None:
    """Hermes onboarding dry-run prints planned files without writing them."""
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "hermes",
            "onboard",
            "--hermes-home",
            str(hermes_home),
            "--api-url",
            "http://backend:8000",
            "--install-prompts",
            "--install-mcp",
            "--dry-run",
        ],
        stdout=stdout,
    )

    payload = loads_json(stdout.getvalue())
    assert exit_code == 0
    assert payload["dry_run"] is True
    assert payload["hermes_home"] == str(hermes_home)
    assert payload["mcp_config"]["mcpServers"]["alexandria"]["args"] == [
        "mcp",
        "serve",
    ]
    assert "alexandria-hermes/policy.yaml" in payload["planned_files"]
    assert (
        "alexandria-hermes/prompts/use-alexandria-library.md"
        in payload["planned_files"]
    )
    assert (
        "alexandria-hermes/prompts/capture-context.md" not in payload["planned_files"]
    )
    assert not (hermes_home / "alexandria-hermes").exists()


def test_hermes_install_writes_local_first_library_when_needed_skill(tmp_path) -> None:
    """Installed skill should route agents local-first, then Alexandria when useful."""
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "hermes",
            "install",
            "--hermes-home",
            str(hermes_home),
            "--api-url",
            "http://backend:8000",
            "--apply",
        ],
        stdout=stdout,
    )

    skill = (
        hermes_home / "skills" / "alexandria-hermes" / "alexandria-library" / "SKILL.md"
    ).read_text(encoding="utf-8")
    operating_loop = (
        hermes_home / "alexandria-hermes" / "prompts" / "alexandria-operating-loop.md"
    ).read_text(encoding="utf-8")
    payload = loads_json(stdout.getvalue())
    assert exit_code == 0
    assert "skills/alexandria-hermes/alexandria-library/SKILL.md" in payload["written"]
    assert skill.startswith("---\nname: alexandria-library")
    assert "local-first" in skill
    assert "Alexandria-when-needed" in skill
    assert "START_HERE" in skill
    assert "current Memory Compact" in skill
    assert "START_HERE" in operating_loop
    assert "local/current context first" in operating_loop
    assert "Long-term memory lookup order" in operating_loop
    assert "alexandria_get_current_memory_compact" in operating_loop
    assert "Do not call Alexandria just because a task starts" in operating_loop


def test_hermes_first_prompt_describes_local_first_onboarding_not_user_coaching() -> (
    None
):
    """First-use guidance should teach agents when to use Alexandria without making users repeat context."""
    prompt = first_conversation_prompt()

    assert "로컬/현재 컨텍스트" in prompt
    assert "current Memory Compact" in prompt
    assert "부족하거나" in prompt
    assert "START_HERE" in prompt
    assert "먼저 RAG status" not in prompt
    assert "확인해 주세요" not in prompt
    assert "매번 Alexandria부터" not in prompt


def test_hermes_operating_loop_documents_context_write_hold() -> None:
    """Operating-loop prompt should tell agents not to call removed write tools."""
    prompt = alexandria_operating_loop_prompt()

    assert "Context write policy" in prompt
    assert "write/capture tools are intentionally disabled" in prompt
    assert "Do not call removed Context Vault write tools" in prompt


def test_hermes_operating_loop_teaches_long_term_memory_lookup_order() -> None:
    """Operating-loop prompt should make current compacts the first durable-memory stop."""
    prompt = alexandria_operating_loop_prompt()

    assert "Long-term memory lookup order" in prompt
    assert "current Memory Compact" in prompt
    assert "mcp_alexandria_alexandria_get_current_memory_compact" in prompt
    assert "alexandria-hermes memory-compacts current" in prompt
    assert "librarian delegation is separate" in prompt


def test_hermes_install_writes_default_enabled_policy_contract(tmp_path) -> None:
    """Hermes install should write a default-on policy contract."""
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "hermes",
            "install",
            "--hermes-home",
            str(hermes_home),
            "--api-url",
            "http://backend:8000",
            "--apply",
        ],
        stdout=stdout,
    )

    policy = (hermes_home / "alexandria-hermes" / "policy.yaml").read_text(
        encoding="utf-8"
    )
    payload = loads_json(stdout.getvalue())
    assert exit_code == 0
    assert "alexandria-hermes/policy.yaml" in payload["written"]
    assert "enabled: true" in policy
    assert "mode: local_first_library_when_needed" in policy
    assert "self_acquisition_enabled: true" in policy
    assert "optional: true" in policy
    assert "hermes_self_acquisition_fallback: true" in policy
    assert "require_explicit_user_request_for_librarian: true" in policy


def test_hermes_policy_cli_toggles_usage_contract(tmp_path) -> None:
    """Hermes policy enable/disable should let users turn Alexandria usage on/off."""
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()
    disable_stdout = io.StringIO()
    status_stdout = io.StringIO()
    enable_stdout = io.StringIO()

    disable_exit = run(
        [
            "--json",
            "hermes",
            "policy",
            "disable",
            "--hermes-home",
            str(hermes_home),
        ],
        stdout=disable_stdout,
    )
    status_exit = run(
        [
            "--json",
            "hermes",
            "policy",
            "status",
            "--hermes-home",
            str(hermes_home),
        ],
        stdout=status_stdout,
    )
    enable_exit = run(
        [
            "--json",
            "hermes",
            "policy",
            "enable",
            "--hermes-home",
            str(hermes_home),
        ],
        stdout=enable_stdout,
    )

    disabled_payload = loads_json(disable_stdout.getvalue())
    status_payload = loads_json(status_stdout.getvalue())
    enabled_payload = loads_json(enable_stdout.getvalue())
    policy_path = hermes_home / "alexandria-hermes" / "policy.yaml"
    assert disable_exit == 0
    assert status_exit == 0
    assert enable_exit == 0
    assert disabled_payload["enabled"] is False
    assert status_payload["enabled"] is False
    assert enabled_payload["enabled"] is True
    assert disabled_payload["policy_path"] == str(policy_path)
    assert "enabled: true" in policy_path.read_text(encoding="utf-8")


def test_hermes_policy_toggle_preserves_custom_contract_settings(tmp_path) -> None:
    """Policy enable/disable should not reset nested user privacy settings."""
    hermes_home = tmp_path / "hermes"
    policy_path = hermes_home / "alexandria-hermes" / "policy.yaml"
    policy_path.parent.mkdir(parents=True)
    policy_path.write_text(
        """# Custom Alexandria policy.
enabled: true
mode: custom_existing_mode

write:
  auto_capture_context: false
  auto_submit_skill_candidates: false

self_acquisition:
  enabled: true
  self_acquisition_enabled: false

librarian:
  enabled: false
  optional: false
  hermes_self_acquisition_fallback: false
""",
        encoding="utf-8",
    )
    disable_stdout = io.StringIO()
    enable_stdout = io.StringIO()

    disable_exit = run(
        [
            "--json",
            "hermes",
            "policy",
            "disable",
            "--hermes-home",
            str(hermes_home),
        ],
        stdout=disable_stdout,
    )
    enable_exit = run(
        [
            "--json",
            "hermes",
            "policy",
            "enable",
            "--hermes-home",
            str(hermes_home),
        ],
        stdout=enable_stdout,
    )

    disabled_payload = loads_json(disable_stdout.getvalue())
    enabled_payload = loads_json(enable_stdout.getvalue())
    policy = policy_path.read_text(encoding="utf-8")
    assert disable_exit == 0
    assert enable_exit == 0
    assert disabled_payload["enabled"] is False
    assert disabled_payload["librarian_enabled"] is False
    assert disabled_payload["librarian_optional"] is False
    assert disabled_payload["self_acquisition_enabled"] is False
    assert disabled_payload["autonomous_curation_enabled"] is False
    assert enabled_payload["enabled"] is True
    assert enabled_payload["librarian_enabled"] is False
    assert "enabled: true" in policy
    assert "mode: custom_existing_mode" in policy
    assert "auto_capture_context: false" in policy
    assert "self_acquisition_enabled: false" in policy
    assert "hermes_self_acquisition_fallback: false" in policy


def test_hermes_install_apply_restart_hint_prints_first_prompt(tmp_path) -> None:
    """hermes install --apply should write prompts/MCP and print restart guidance."""
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "hermes",
            "install",
            "--hermes-home",
            str(hermes_home),
            "--api-url",
            "http://backend:8000",
            "--apply",
            "--restart-hint",
        ],
        stdout=stdout,
    )

    payload = loads_json(stdout.getvalue())
    assert exit_code == 0
    assert payload["dry_run"] is False
    assert "restart" in payload["restart_hint"].lower()
    assert "Alexandria-Hermes가 설치되어 있습니다" in payload["first_prompt"]
    assert (hermes_home / "alexandria-hermes" / "mcp-config.json").exists()
    assert (
        hermes_home / "alexandria-hermes" / "prompts" / "alexandria-operating-loop.md"
    ).exists()


def test_hermes_doctor_deep_reports_readiness_checks(tmp_path) -> None:
    """hermes doctor --deep should expose operator readiness checks."""
    hermes_home = tmp_path / "hermes"
    prompts_dir = hermes_home / "alexandria-hermes" / "prompts"
    prompts_dir.mkdir(parents=True)
    (prompts_dir / "alexandria-operating-loop.md").write_text(
        "# Loop", encoding="utf-8"
    )
    (hermes_home / "alexandria-hermes" / "mcp-config.json").write_text(
        "{}", encoding="utf-8"
    )
    stdout = io.StringIO()

    exit_code = run(
        ["--json", "hermes", "doctor", "--hermes-home", str(hermes_home), "--deep"],
        stdout=stdout,
    )

    payload = loads_json(stdout.getvalue())
    assert exit_code == 0
    assert payload["deep"] is True
    assert payload["checks"]["operating_loop_prompt"] == "OK"
    assert payload["checks"]["prompt_item_type_constraint"] == "CHECK_MANUALLY"
    assert payload["restart_needed"] is True


def test_hermes_json_output_redacts_mcp_operator_key(tmp_path) -> None:
    """Hermes JSON output should never echo operator keys from flags or env."""
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "hermes",
            "install-mcp",
            "--hermes-home",
            str(hermes_home),
            "--api-url",
            "http://backend:8000",
            "--operator-api-key",
            "secret-token",
            "--dry-run",
        ],
        stdout=stdout,
    )

    output = stdout.getvalue()
    payload = loads_json(output)
    assert exit_code == 0
    assert "secret-token" not in output
    assert (
        payload["mcp_config"]["mcpServers"]["alexandria"]["env"][
            "ALEXANDRIA_OPERATOR_API_KEY"
        ]
        == "<REDACTED>"
    )


def test_hermes_install_mcp_uses_api_env_defaults(monkeypatch, tmp_path) -> None:
    """Hermes install-mcp preserves API URL and operator-key environment defaults."""
    monkeypatch.setenv("ALEXANDRIA_API_URL", "http://env-backend:8000")
    monkeypatch.setenv("ALEXANDRIA_OPERATOR_API_KEY", "env-secret-token")
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "hermes",
            "install-mcp",
            "--hermes-home",
            str(hermes_home),
            "--dry-run",
        ],
        stdout=stdout,
    )

    output = stdout.getvalue()
    payload = loads_json(output)
    env = payload["mcp_config"]["mcpServers"]["alexandria"]["env"]
    assert exit_code == 0
    assert env["ALEXANDRIA_API_URL"] == "http://env-backend:8000"
    assert env["ALEXANDRIA_OPERATOR_API_KEY"] == "<REDACTED>"
    assert "env-secret-token" not in output


def test_hermes_install_prompts_skips_existing_file_without_overwrite(tmp_path) -> None:
    """Hermes onboarding never overwrites existing files by default."""
    hermes_home = tmp_path / "hermes"
    existing = (
        hermes_home / "alexandria-hermes" / "prompts" / "use-alexandria-library.md"
    )
    existing.parent.mkdir(parents=True)
    existing.write_text("custom", encoding="utf-8")
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "hermes",
            "install-prompts",
            "--hermes-home",
            str(hermes_home),
        ],
        stdout=stdout,
    )

    payload = loads_json(stdout.getvalue())
    assert exit_code == 0
    assert existing.read_text(encoding="utf-8") == "custom"
    assert "alexandria-hermes/prompts/use-alexandria-library.md" in payload["skipped"]
    assert (
        "alexandria-hermes/prompts/request-skill-acquisition.md" in payload["written"]
    )


def test_hermes_install_prompts_includes_self_acquisition_loop(tmp_path) -> None:
    """Hermes prompt install should teach search-first self-acquisition."""
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "hermes",
            "install-prompts",
            "--hermes-home",
            str(hermes_home),
        ],
        stdout=stdout,
    )

    rules = (hermes_home / "alexandria-hermes" / "alexandria-rules.md").read_text(
        encoding="utf-8"
    )
    request_skill = (
        hermes_home / "alexandria-hermes" / "prompts" / "request-skill-acquisition.md"
    ).read_text(encoding="utf-8")
    operating_loop = (
        hermes_home / "alexandria-hermes" / "prompts" / "alexandria-operating-loop.md"
    ).read_text(encoding="utf-8")
    assert exit_code == 0
    assert "Alexandria when needed, then Hermes self-acquisition" in rules
    assert "alexandria_search" in request_skill
    assert "alexandria_start_skill_acquisition" in request_skill
    assert "alexandria_skill_acquisition_job_status" in request_skill
    assert "alexandria_complete_skill_acquisition" in request_skill
    assert "backend no longer persists skill records to SQLite" in request_skill
    assert "mcp_alexandria_alexandria_start_skill_acquisition" in operating_loop
    assert "mcp_alexandria_alexandria_skill_acquisition_job_status" in operating_loop
    assert "mcp_alexandria_alexandria_complete_skill_acquisition" in operating_loop
    assert "SQLite-backed skill/prompt CRUD has been removed" in operating_loop
    assert "alexandria_submit_skill_candidate" not in operating_loop
    assert "local/current context first" in operating_loop
    assert "Prompt preservation policy" in operating_loop


def test_hermes_install_mcp_overwrite_creates_backup(tmp_path) -> None:
    """Explicit overwrite preserves the previous MCP config as a timestamp-free backup."""
    hermes_home = tmp_path / "hermes"
    config = hermes_home / "alexandria-hermes" / "mcp-config.json"
    config.parent.mkdir(parents=True)
    config.write_text('{"old": true}', encoding="utf-8")
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "hermes",
            "install-mcp",
            "--hermes-home",
            str(hermes_home),
            "--api-url",
            "http://backend:8000",
            "--overwrite",
        ],
        stdout=stdout,
    )

    payload = loads_json(stdout.getvalue())
    assert exit_code == 0
    assert "alexandria-hermes/mcp-config.json" in payload["written"]
    assert payload["backups"] == ["alexandria-hermes/mcp-config.json.bak"]
    assert (config.parent / "mcp-config.json.bak").read_text(encoding="utf-8") == (
        '{"old": true}'
    )
    assert (
        loads_json(config.read_text(encoding="utf-8"))["mcpServers"]["alexandria"][
            "env"
        ]["ALEXANDRIA_API_URL"]
        == "http://backend:8000"
    )


def test_hermes_doctor_reports_missing_required_home_when_no_source(
    monkeypatch,
) -> None:
    """Hermes doctor exposes HERMES_HOME_REQUIRED when no path can be resolved."""
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.setenv("ALEXANDRIA_HERMES_CONFIG", "")
    monkeypatch.setenv("HOME", "/tmp/alexandria-hermes-no-home-for-test")
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = run(
        ["--json", "hermes", "doctor", "--require-home"],
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 1
    assert "HERMES_HOME_REQUIRED" in stderr.getvalue()


def test_cli_asks_librarian_for_delegated_work_as_json() -> None:
    """Librarian ask command exposes the backend collaboration contract."""
    transport, calls = _transport(
        {
            "job_id": "librarian-job-abc123",
            "status": "ACCEPTED",
            "decision": "DELEGATE_TO_LIBRARIAN",
        }
    )
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "librarian",
            "ask",
            "Need an OAuth review skill",
            "--delegate-to-librarian",
            "--project",
            "alexandria-hermes",
            "--librarian-profile-id",
            "profile-1",
            "--librarian-model",
            "gpt-5.5",
            "--librarian-role-prompt",
            "Use project memory first.",
            "--max-librarian-agents",
            "2",
        ],
        transport=transport,
        stdout=stdout,
    )

    request_body = loads_json((calls[0][2] or b"{}").decode())
    assert exit_code == 0
    assert calls[0][0] == "POST"
    assert calls[0][1] == "http://localhost:8000/librarians/ask"
    assert request_body == {
        "prompt": "Need an OAuth review skill",
        "agent_name": "Hermes",
        "delegate_to_librarian": True,
        "project": "alexandria-hermes",
        "librarian_profile_id": "profile-1",
        "librarian_model": "gpt-5.5",
        "librarian_role_prompt": "Use project memory first.",
        "max_librarian_agents": 2,
    }
    assert loads_json(stdout.getvalue())["job_id"] == "librarian-job-abc123"


def test_cli_previews_librarian_brief_packet() -> None:
    """Librarian brief-preview CLI should call the compact packet endpoint."""
    transport, calls = _transport({"packet_markdown": "# Packet"})
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "librarian",
            "brief-preview",
            "Need OAuth evidence",
            "--project",
            "alexandria-hermes",
            "--max-input-chars",
            "3000",
            "--max-source-refs",
            "4",
        ],
        transport=transport,
        stdout=stdout,
    )

    request_body = loads_json((calls[0][2] or b"{}").decode())
    assert exit_code == 0
    assert calls[0][0] == "POST"
    assert calls[0][1] == "http://localhost:8000/librarians/brief-preview"
    assert request_body == {
        "prompt": "Need OAuth evidence",
        "budget": {"max_input_chars": 3000, "max_source_refs": 4},
        "project": "alexandria-hermes",
    }
    assert loads_json(stdout.getvalue())["packet_markdown"] == "# Packet"


def test_cli_lists_memory_compacts_with_project_and_status_filters() -> None:
    """Memory Compact list should use first-class compact endpoints."""
    transport, calls = _transport(
        {
            "items": [
                {
                    "id": "compact-1",
                    "status": "CURRENT",
                    "project": "alexandria-hermes",
                    "covered_to": "2026-05-17T00:00:00Z",
                }
            ],
            "total": 1,
        }
    )
    stdout = io.StringIO()

    exit_code = run(
        [
            "memory-compacts",
            "list",
            "--project",
            "alexandria-hermes",
            "--status",
            "CURRENT",
            "--limit",
            "3",
            "--offset",
            "2",
        ],
        transport=transport,
        stdout=stdout,
    )

    assert exit_code == 0
    assert calls[0][0] == "GET"
    assert (
        calls[0][1]
        == "http://localhost:8000/memory/compacts?limit=3&offset=2&project=alexandria-hermes&status=CURRENT"
    )
    assert "compact-1\tCURRENT\talexandria-hermes" in stdout.getvalue()


def test_cli_reads_current_and_selected_memory_compacts() -> None:
    """Memory Compact current/get commands should lazy-load selected artifacts."""
    transport, calls = _transport(
        {
            "id": "compact/1",
            "status": "CURRENT",
            "project": "alexandria-hermes",
        }
    )
    current_stdout = io.StringIO()
    get_stdout = io.StringIO()

    current_exit = run(
        ["memory-compacts", "current", "--project", "alexandria-hermes"],
        transport=transport,
        stdout=current_stdout,
    )
    get_exit = run(
        ["--json", "memory-compacts", "get", "compact/1"],
        transport=transport,
        stdout=get_stdout,
    )

    assert current_exit == 0
    assert get_exit == 0
    assert calls[0][0] == "GET"
    assert (
        calls[0][1]
        == "http://localhost:8000/memory/compacts/current?project=alexandria-hermes"
    )
    assert calls[1][0] == "GET"
    assert calls[1][1] == "http://localhost:8000/memory/compacts/compact%2F1"
    assert "CURRENT compact/1 alexandria-hermes" in current_stdout.getvalue()
    assert loads_json(get_stdout.getvalue())["id"] == "compact/1"


def test_cli_hard_deletes_context_and_memory_compact() -> None:
    """Context and Memory Compact CLI delete commands should hit hard-delete APIs."""
    transport, calls = _transport(None)
    context_stdout = io.StringIO()
    compact_stdout = io.StringIO()

    context_exit = run(
        ["context", "delete", "ctx/1"],
        transport=transport,
        stdout=context_stdout,
    )
    compact_exit = run(
        ["memory-compacts", "delete", "compact/1"],
        transport=transport,
        stdout=compact_stdout,
    )

    assert context_exit == 0
    assert compact_exit == 0
    assert [(call[0], call[1]) for call in calls] == [
        ("DELETE", "http://localhost:8000/memory/contexts/ctx%2F1"),
        ("DELETE", "http://localhost:8000/memory/compacts/compact%2F1"),
    ]
    assert "deleted context ctx/1" in context_stdout.getvalue()
    assert "deleted memory compact compact/1" in compact_stdout.getvalue()


def test_cli_previews_librarian_route_without_delegation() -> None:
    """Librarian route-preview should not queue delegated work."""
    transport, calls = _transport(
        {
            "job_id": "librarian-job-preview",
            "status": "GUIDANCE_ONLY",
            "decision": "SUGGEST_HERMES_RESEARCH",
            "route_preview": ["Hermes direct search first"],
        }
    )
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "librarian",
            "route-preview",
            "Need an OAuth review skill",
            "--project",
            "alexandria-hermes",
            "--librarian-profile-id",
            "profile-1",
            "--max-librarian-agents",
            "2",
        ],
        transport=transport,
        stdout=stdout,
    )

    request_body = loads_json((calls[0][2] or b"{}").decode())
    assert exit_code == 0
    assert calls[0][0] == "POST"
    assert calls[0][1] == "http://localhost:8000/librarians/route-preview"
    assert request_body == {
        "prompt": "Need an OAuth review skill",
        "agent_name": "Hermes",
        "delegate_to_librarian": False,
        "project": "alexandria-hermes",
        "librarian_profile_id": "profile-1",
        "max_librarian_agents": 2,
    }
    assert loads_json(stdout.getvalue())["route_preview"] == [
        "Hermes direct search first"
    ]


def test_cli_starts_librarian_oauth_with_user_instructions_without_token_fields() -> (
    None
):
    """OAuth start output should include user instructions but omit tokens."""
    transport, calls = _transport(
        {
            "provider_id": "provider-1",
            "status": "pending",
            "user_code": "SECRET-CODE",
            "verification_uri": "https://login.example/device",
            "verification_uri_complete": (
                "https://login.example/device?user_code=SECRET-CODE"
            ),
            "oauth_access_token": "secret-access-token",
            "expires_at": "2026-05-15T12:10:00Z",
            "interval_seconds": 5,
        }
    )
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "--operator-api-key",
            TEST_OPERATOR_API_KEY,
            "librarian",
            "oauth-start",
            "provider/1",
        ],
        transport=transport,
        stdout=stdout,
    )

    printed = stdout.getvalue()
    assert exit_code == 0
    assert calls[0][0] == "POST"
    assert (
        calls[0][1]
        == "http://localhost:8000/settings/connections/provider%2F1/oauth/start"
    )
    assert calls[0][3]["X-Alexandria-Operator-Key"] == TEST_OPERATOR_API_KEY
    assert "oauth_access_token" not in printed
    assert "device_code" not in printed
    assert loads_json(printed) == {
        "provider_id": "provider-1",
        "status": "pending",
        "user_code": "SECRET-CODE",
        "verification_uri": "https://login.example/device",
        "verification_uri_complete": (
            "https://login.example/device?user_code=SECRET-CODE"
        ),
        "expires_at": "2026-05-15T12:10:00Z",
        "interval_seconds": 5,
    }


def test_cli_starts_librarian_oauth_text_with_user_instructions() -> None:
    """OAuth start text output should be enough to complete the device flow."""
    transport, calls = _transport(
        {
            "provider_id": "provider-1",
            "status": "pending",
            "user_code": "SECRET-CODE",
            "verification_uri": "https://login.example/device",
            "verification_uri_complete": (
                "https://login.example/device?user_code=SECRET-CODE"
            ),
            "oauth_access_token": "secret-access-token",
        }
    )
    stdout = io.StringIO()

    exit_code = run(
        ["librarian", "oauth-start", "provider/1"],
        transport=transport,
        stdout=stdout,
    )

    printed = stdout.getvalue()
    assert exit_code == 0
    assert calls[0][0] == "POST"
    assert "https://login.example/device?user_code=SECRET-CODE" in printed
    assert "code SECRET-CODE" in printed
    assert "oauth_access_token" not in printed
    assert "secret-access-token" not in printed


def test_cli_librarian_oauth_lifecycle_commands_call_matching_routes() -> None:
    """OAuth poll/status/refresh commands should call lifecycle backend routes."""
    transport, calls = _transport(
        {
            "provider_id": "provider-1",
            "status": "connected",
            "connected": True,
            "refresh_required": False,
            "message": None,
        }
    )
    stdout = io.StringIO()

    exit_codes = [
        run(
            ["librarian", "oauth-poll", "provider-1"],
            transport=transport,
            stdout=stdout,
        ),
        run(
            ["librarian", "oauth-status", "provider-1"],
            transport=transport,
            stdout=stdout,
        ),
        run(
            ["librarian", "oauth-refresh", "provider-1"],
            transport=transport,
            stdout=stdout,
        ),
    ]

    assert exit_codes == [0, 0, 0]
    assert [(method, url) for method, url, *_ in calls] == [
        (
            "POST",
            "http://localhost:8000/settings/connections/provider-1/oauth/poll",
        ),
        (
            "GET",
            "http://localhost:8000/settings/connections/provider-1/oauth/status",
        ),
        (
            "POST",
            "http://localhost:8000/settings/connections/provider-1/oauth/refresh",
        ),
    ]
    assert "token" not in stdout.getvalue().lower()


def test_cli_creates_codex_oauth_provider_with_safe_payload() -> None:
    """Provider create-codex-oauth should post pending OAuth config without secrets."""
    transport, calls = _transport(
        {
            "id": "provider-1",
            "name": "Codex OAuth",
            "provider_type": "OPENAI_CODEX",
            "auth_type": "OAUTH",
        }
    )
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "librarian",
            "providers",
            "create-codex-oauth",
            "--name",
            "Codex OAuth",
        ],
        transport=transport,
        stdout=stdout,
    )

    body = loads_json((calls[0][2] or b"{}").decode())
    assert exit_code == 0
    assert calls[0][0] == "POST"
    assert calls[0][1] == "http://localhost:8000/settings/connections"
    assert body["provider_type"] == "OPENAI_CODEX"
    assert body["auth_type"] == "OAUTH"
    assert "api_key" not in body
    assert "device_authorization_url" in body["config"]
    assert "client_id" not in body["config"]


def test_cli_connects_codex_oauth_after_creating_provider_without_token_leak() -> None:
    """Provider connect-codex-oauth should create provider then print redacted OAuth start."""
    calls: list[RecordedCall] = []

    def fake_transport(
        method: str,
        url: str,
        body: bytes | None,
        headers: HttpHeaders,
        timeout: float,
    ) -> tuple[int, bytes]:
        calls.append((method, url, body, headers, timeout))
        if len(calls) == 1:
            payload = {"id": "provider-1", "name": "Codex OAuth"}
        else:
            payload = {
                "provider_id": "provider-1",
                "status": "pending",
                "user_code": "USER-CODE",
                "verification_uri": "https://auth.openai.com/codex/device",
                "oauth_access_token": "secret-token",
            }
        return 200, dumps_json(payload)

    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "librarian",
            "providers",
            "connect-codex-oauth",
            "--name",
            "Codex OAuth",
        ],
        transport=fake_transport,
        stdout=stdout,
    )

    printed = stdout.getvalue()
    assert exit_code == 0
    assert [(method, url) for method, url, *_ in calls] == [
        ("POST", "http://localhost:8000/settings/connections"),
        ("POST", "http://localhost:8000/settings/connections/provider-1/oauth/start"),
    ]
    provider_body = loads_json((calls[0][2] or b"{}").decode())
    assert "client_id" not in provider_body["config"]
    assert "secret-token" not in printed
    assert loads_json(printed)["oauth"]["user_code"] == "USER-CODE"


def test_cli_creates_openai_provider_from_env_without_printing_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Provider create-openai should read API key from env and not echo it."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret")
    transport, calls = _transport({"id": "provider-1", "name": "OpenAI"})
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "librarian",
            "providers",
            "create-openai",
            "--name",
            "OpenAI",
            "--api-key-env",
            "OPENAI_API_KEY",
        ],
        transport=transport,
        stdout=stdout,
    )

    body = loads_json((calls[0][2] or b"{}").decode())
    assert exit_code == 0
    assert body["api_key"] == "sk-test-secret"
    assert "sk-test-secret" not in stdout.getvalue()


def test_cli_creates_librarian_profile_with_role_specialties_and_delegate_limit(
    tmp_path,
) -> None:
    """Profile create should post role, specialties, delegate limit, and role prompt file."""
    prompt_file = tmp_path / "python-fastapi.md"
    prompt_file.write_text("Focus on Python, FastAPI, and OAuth.", encoding="utf-8")
    transport, calls = _transport({"id": "profile-1", "name": "Python Librarian"})
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "librarian",
            "profiles",
            "create",
            "--name",
            "Python Librarian",
            "--role",
            "SPECIALIST",
            "--specialty",
            "python",
            "--specialty",
            "fastapi",
            "--provider-id",
            "provider-1",
            "--model",
            "gpt-5.5",
            "--delegate-limit",
            "2",
            "--role-prompt-file",
            str(prompt_file),
            "--routing-priority",
            "20",
        ],
        transport=transport,
        stdout=stdout,
    )

    body = loads_json((calls[0][2] or b"{}").decode())
    assert exit_code == 0
    assert calls[0][1] == "http://localhost:8000/librarians/profiles"
    assert body["librarian_role"] == "SPECIALIST"
    assert body["librarian_specialties"] == ["python", "fastapi"]
    assert body["capabilities"] == ["python", "fastapi"]
    assert body["max_librarian_agents"] == 2
    assert body["librarian_routing_priority"] == 20
    assert body["librarian_role_prompt"] == "Focus on Python, FastAPI, and OAuth."


def test_cli_updates_librarian_profile_specialties_by_reading_current_profile() -> None:
    """Profile update should add/remove specialties before patching backend."""
    calls: list[RecordedCall] = []

    def fake_transport(
        method: str,
        url: str,
        body: bytes | None,
        headers: HttpHeaders,
        timeout: float,
    ) -> tuple[int, bytes]:
        calls.append((method, url, body, headers, timeout))
        if method == "GET":
            payload = {
                "id": "profile-1",
                "librarian_specialties": ["quality", "oauth"],
            }
        else:
            payload = {
                "id": "profile-1",
                "librarian_specialties": ["oauth", "security"],
            }
        return 200, dumps_json(payload)

    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "librarian",
            "profiles",
            "update",
            "profile-1",
            "--add-specialty",
            "security",
            "--remove-specialty",
            "quality",
            "--delegate-limit",
            "3",
        ],
        transport=fake_transport,
        stdout=stdout,
    )

    patch_body = loads_json((calls[1][2] or b"{}").decode())
    assert exit_code == 0
    assert [(method, url) for method, url, *_ in calls] == [
        ("GET", "http://localhost:8000/librarians/profiles/profile-1"),
        ("PATCH", "http://localhost:8000/librarians/profiles/profile-1"),
    ]
    assert patch_body["librarian_specialties"] == ["oauth", "security"]
    assert patch_body["capabilities"] == ["oauth", "security"]
    assert patch_body["max_librarian_agents"] == 3


def test_cli_ask_delegate_aliases_map_to_backend_contract() -> None:
    """Ask aliases should preserve old backend max_librarian_agents contract."""
    transport, calls = _transport({"job_id": "job-1", "route_preview": []})
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "librarian",
            "ask",
            "Need FastAPI OAuth help",
            "--delegate",
            "--delegate-limit",
            "2",
            "--specialty",
            "fastapi",
            "--specialty",
            "oauth",
        ],
        transport=transport,
        stdout=stdout,
    )

    body = loads_json((calls[0][2] or b"{}").decode())
    assert exit_code == 0
    assert body["delegate_to_librarian"] is True
    assert body["max_librarian_agents"] == 2
    assert body["routing_specialties"] == ["fastapi", "oauth"]
