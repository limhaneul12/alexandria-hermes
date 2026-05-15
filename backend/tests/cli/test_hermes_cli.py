"""Behavior tests for the Hermes CLI HTTP client."""

from __future__ import annotations

import io
import json
from collections.abc import Callable

import pytest
from app.cli import HttpHeaders, run

RecordedCall = tuple[str, str, bytes | None, HttpHeaders, float]


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
        response = json.dumps(response_payload).encode()
        return 200, response

    return fake_transport, calls


def test_cli_scans_minio_candidates_as_json_when_requested() -> None:
    """MINIO scan exposes import candidates for agents without opening the UI."""
    transport, calls = _transport(
        [
            {
                "id": "candidate-1",
                "item_type": "SKILL",
                "object_key": "skills/a.md",
            }
        ]
    )
    stdout = io.StringIO()

    exit_code = run(
        ["--json", "minio", "scan", "--limit", "5"],
        transport=transport,
        stdout=stdout,
    )

    assert exit_code == 0
    assert calls[0][0] == "GET"
    assert (
        calls[0][1] == "http://localhost:8000/storage/minio/import-candidates?limit=5"
    )
    assert json.loads(stdout.getvalue())[0]["id"] == "candidate-1"


def test_cli_imports_minio_candidates_with_bounded_request_body() -> None:
    """MINIO import sends a linked-import request and prints the sync summary."""
    transport, calls = _transport(
        {"imported_count": 2, "skipped_count": 1, "item_ids": ["a", "b"]}
    )
    stdout = io.StringIO()

    exit_code = run(
        ["minio", "import", "--limit", "2000"],
        transport=transport,
        stdout=stdout,
    )

    assert exit_code == 0
    assert calls[0][0] == "POST"
    assert calls[0][1] == "http://localhost:8000/storage/minio/import"
    assert json.loads((calls[0][2] or b"{}").decode()) == {"limit": 1000}
    assert "2 imported, 1 skipped" in stdout.getvalue()


@pytest.mark.parametrize(
    ("argv", "invalid_value"),
    [
        (
            [
                "skills",
                "create",
                "--title",
                "Skill",
                "--purpose",
                "Purpose",
                "--risk-level",
                "BOGUS",
            ],
            "BOGUS",
        ),
        (
            [
                "prompts",
                "create",
                "--title",
                "Prompt",
                "--format",
                "YAML",
            ],
            "YAML",
        ),
        (["library", "list", "--type", "INVALID"], "INVALID"),
        (["minio", "scan", "--type", "BAD"], "BAD"),
    ],
)
def test_cli_rejects_invalid_choice_before_http_request(
    argv: list[str],
    invalid_value: str,
) -> None:
    """CLI choice validation rejects invalid enum values before HTTP I/O."""
    transport, calls = _transport({"unexpected": True})
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = run(argv, transport=transport, stdout=stdout, stderr=stderr)

    assert exit_code != 0
    assert invalid_value in stderr.getvalue()
    assert calls == []


def test_cli_creates_manual_skill_from_content_file(tmp_path) -> None:
    """Manual skill creation remains available outside the web form."""
    content_file = tmp_path / "skill.md"
    content_file.write_text(
        "# FastAPI skill\nUse dependency overrides.", encoding="utf-8"
    )
    transport, calls = _transport(
        {"id": "skill-1", "title": "FastAPI skill", "item_type": "SKILL"}
    )
    stdout = io.StringIO()

    exit_code = run(
        [
            "skills",
            "create",
            "--title",
            "FastAPI skill",
            "--purpose",
            "Teach agent testing",
            "--content-file",
            str(content_file),
            "--tag",
            "fastapi",
            "--tool",
            "pytest",
            "--active",
        ],
        transport=transport,
        stdout=stdout,
    )

    request_body = json.loads((calls[0][2] or b"{}").decode())
    assert exit_code == 0
    assert calls[0][0] == "POST"
    assert calls[0][1] == "http://localhost:8000/skills"
    assert request_body == {
        "title": "FastAPI skill",
        "summary": None,
        "content": "# FastAPI skill\nUse dependency overrides.",
        "category_id": None,
        "tags": ["fastapi"],
        "purpose": "Teach agent testing",
        "input_schema": {},
        "output_schema": {},
        "usage_example": None,
        "required_tools": ["pytest"],
        "risk_level": "LOW",
        "version": "1.0.0",
        "created_by_name": "Hermes CLI",
        "status": "ACTIVE",
    }
    assert "created skill skill-1" in stdout.getvalue()


def test_cli_deletes_skill_by_id() -> None:
    """Skill deletion is available from CLI like the detail-page delete action."""
    transport, calls = _transport(None)
    stdout = io.StringIO()

    exit_code = run(
        ["skills", "delete", "skill-1"],
        transport=transport,
        stdout=stdout,
    )

    assert exit_code == 0
    assert calls[0][0] == "DELETE"
    assert calls[0][1] == "http://localhost:8000/skills/skill-1"
    assert "deleted skill skill-1" in stdout.getvalue()


def test_cli_creates_folder_with_parent_id() -> None:
    """Folder creation is available from CLI like the UI create-folder action."""
    transport, calls = _transport(
        {
            "id": "folder-1",
            "name": "Backend",
            "parent_id": "root-1",
            "position": 0,
            "created_at": "2026-05-14T00:00:00Z",
            "updated_at": "2026-05-14T00:00:00Z",
        }
    )
    stdout = io.StringIO()

    exit_code = run(
        ["folders", "create", "--name", "Backend", "--parent-id", "root-1"],
        transport=transport,
        stdout=stdout,
    )

    assert exit_code == 0
    assert calls[0][0] == "POST"
    assert calls[0][1] == "http://localhost:8000/categories"
    assert json.loads((calls[0][2] or b"{}").decode()) == {
        "name": "Backend",
        "parent_id": "root-1",
    }
    assert "created folder folder-1: Backend" in stdout.getvalue()


def test_cli_lists_folder_tree_as_json_for_agents() -> None:
    """Agents can inspect the folder tree in the same hierarchy used by the UI."""
    transport, calls = _transport(
        [
            {
                "id": "root-1",
                "name": "Backend",
                "parent_id": None,
                "position": 0,
                "children": [],
            }
        ]
    )
    stdout = io.StringIO()

    exit_code = run(
        ["--json", "folders", "list", "--tree"],
        transport=transport,
        stdout=stdout,
    )

    assert exit_code == 0
    assert calls[0][0] == "GET"
    assert calls[0][1] == "http://localhost:8000/categories/tree"
    assert json.loads(stdout.getvalue())[0]["name"] == "Backend"


def test_cli_deletes_folder_by_id() -> None:
    """Folder deletion is available from CLI like the UI delete-folder action."""
    transport, calls = _transport(None)
    stdout = io.StringIO()

    exit_code = run(
        ["folders", "delete", "folder-1"],
        transport=transport,
        stdout=stdout,
    )

    assert exit_code == 0
    assert calls[0][0] == "DELETE"
    assert calls[0][1] == "http://localhost:8000/categories/folder-1"
    assert "deleted folder folder-1" in stdout.getvalue()


def test_cli_lists_library_items_with_ui_filters() -> None:
    """The CLI can browse the same filtered item list exposed to the UI."""
    transport, calls = _transport(
        [{"id": "skill-1", "item_type": "SKILL", "title": "FastAPI"}]
    )
    stdout = io.StringIO()

    exit_code = run(
        [
            "library",
            "list",
            "--type",
            "SKILL",
            "--folder-id",
            "folder-1",
            "--query",
            "fastapi",
            "--limit",
            "5",
        ],
        transport=transport,
        stdout=stdout,
    )

    assert exit_code == 0
    assert calls[0][0] == "GET"
    assert calls[0][1] == (
        "http://localhost:8000/items?limit=5&offset=0&item_type=SKILL"
        "&category_id=folder-1&q=fastapi"
    )
    assert "skill-1" in stdout.getvalue()


def test_cli_searches_library_items() -> None:
    """The CLI exposes the UI search path for shell and agent use."""
    transport, calls = _transport(
        [{"id": "knowledge-1", "item_type": "KNOWLEDGE", "title": "Indexing"}]
    )
    stdout = io.StringIO()

    exit_code = run(
        ["library", "search", "postgres index"],
        transport=transport,
        stdout=stdout,
    )

    assert exit_code == 0
    assert calls[0][0] == "GET"
    assert calls[0][1] == "http://localhost:8000/search?q=postgres+index"
    assert "knowledge-1" in stdout.getvalue()


def test_repo_cli_shim_runs_help_without_uv_run() -> None:
    """Repository shim lets users inspect CLI help without prefixing uv run."""
    import subprocess
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [str(repo_root / "bin" / "alexandria-hermes"), "skills", "--help"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert all(
        command in result.stdout for command in ("list", "get", "create", "delete")
    )


def test_cli_creates_prompt_from_content_file_for_agents(tmp_path) -> None:
    """Prompt creation supports agent-authored files without requiring the UI."""
    content_file = tmp_path / "review.prompt.md"
    content_file.write_text("Review this diff: {{diff}}", encoding="utf-8")
    transport, calls = _transport(
        {"id": "prompt-1", "title": "Review prompt", "item_type": "PROMPT"}
    )
    stdout = io.StringIO()

    exit_code = run(
        [
            "prompts",
            "create",
            "--title",
            "Review prompt",
            "--content-file",
            str(content_file),
            "--domain",
            "DEVELOPMENT",
            "--task-type",
            "CODE_REVIEW",
            "--var",
            "diff:required:검토할 diff",
            "--created-by",
            "Backend Agent",
            "--created-by-type",
            "AGENT",
            "--source-type",
            "AGENT_SUBMITTED",
            "--active",
        ],
        transport=transport,
        stdout=stdout,
    )

    request_body = json.loads((calls[0][2] or b"{}").decode())
    assert exit_code == 0
    assert calls[0][0] == "POST"
    assert calls[0][1] == "http://localhost:8000/prompts"
    assert request_body["content"] == "Review this diff: {{diff}}"
    assert request_body["prompt_domain"] == "DEVELOPMENT"
    assert request_body["prompt_task_type"] == "CODE_REVIEW"
    assert request_body["input_variables"] == [
        {
            "name": "diff",
            "required": True,
            "description": "검토할 diff",
            "default_value": None,
            "example": None,
            "input_type": "text",
        }
    ]
    assert request_body["created_by_type"] == "AGENT"
    assert request_body["source_type"] == "AGENT_SUBMITTED"
    assert request_body["status"] == "ACTIVE"
    assert "created prompt prompt-1" in stdout.getvalue()


def test_cli_uses_prompt_and_records_usage() -> None:
    """Prompt use prints content and records usage history for agents."""
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
            return 200, json.dumps({"id": "prompt-1", "content": "Use me"}).encode()
        return 200, json.dumps({"id": "usage-1"}).encode()

    stdout = io.StringIO()

    exit_code = run(
        ["prompts", "use", "prompt-1", "--actor-name", "Backend Agent"],
        transport=fake_transport,
        stdout=stdout,
    )

    assert exit_code == 0
    assert calls[0][0] == "GET"
    assert calls[0][1] == "http://localhost:8000/prompts/prompt-1"
    assert calls[1][0] == "POST"
    assert calls[1][1] == "http://localhost:8000/usage"
    assert json.loads((calls[1][2] or b"{}").decode())["item_type"] == "PROMPT"
    assert "Use me" in stdout.getvalue()


def test_cli_lints_context_file_as_json(tmp_path) -> None:
    """Context lint sends Markdown content to backend and returns agent-readable JSON."""
    content_file = tmp_path / "handoff.md"
    content_file.write_text("# Handoff\n\n## Summary\nReady.\n", encoding="utf-8")
    transport, calls = _transport({"ok": True, "status": "SAVED", "score": 100})
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "context",
            "lint",
            str(content_file),
            "--title",
            "Sprint handoff",
            "--kind",
            "HANDOFF",
            "--tag",
            "sprint",
        ],
        transport=transport,
        stdout=stdout,
    )

    request_body = json.loads((calls[0][2] or b"{}").decode())
    assert exit_code == 0
    assert calls[0][0] == "POST"
    assert calls[0][1] == "http://localhost:8000/library/contexts/lint"
    assert request_body == {
        "kind": "HANDOFF",
        "title": "Sprint handoff",
        "content": "# Handoff\n\n## Summary\nReady.",
        "summary": None,
        "project": None,
        "source_agent": "Hermes",
        "tags": ["sprint"],
    }
    assert json.loads(stdout.getvalue())["status"] == "SAVED"


def test_cli_saves_and_recalls_context_with_context_pack_json(tmp_path) -> None:
    """Context save and recall expose the backend Context Pack contract."""
    content_file = tmp_path / "decision.md"
    content_file.write_text(
        "# Decision\n\n## Summary\nUse FTS fallback.", encoding="utf-8"
    )
    calls: list[RecordedCall] = []

    def fake_transport(
        method: str,
        url: str,
        body: bytes | None,
        headers: HttpHeaders,
        timeout: float,
    ) -> tuple[int, bytes]:
        calls.append((method, url, body, headers, timeout))
        if url.endswith("/library/contexts"):
            return 201, json.dumps({"id": "ctx-1", "title": "Decision"}).encode()
        return 200, json.dumps({"context_pack": "# Pack", "matches": []}).encode()

    save_stdout = io.StringIO()
    recall_stdout = io.StringIO()

    save_exit = run(
        [
            "--json",
            "context",
            "save",
            "--title",
            "Decision",
            "--kind",
            "DECISION",
            "--source-type",
            "IMPORTED",
            "--content-file",
            str(content_file),
        ],
        transport=fake_transport,
        stdout=save_stdout,
    )
    recall_exit = run(
        ["--json", "context", "recall", "FTS fallback", "--strategy", "FTS_ONLY"],
        transport=fake_transport,
        stdout=recall_stdout,
    )

    save_body = json.loads((calls[0][2] or b"{}").decode())
    recall_body = json.loads((calls[1][2] or b"{}").decode())
    assert save_exit == 0
    assert recall_exit == 0
    assert calls[0][0] == "POST"
    assert calls[0][1] == "http://localhost:8000/library/contexts"
    assert save_body["kind"] == "DECISION"
    assert save_body["source_type"] == "IMPORTED"
    assert save_body["content"] == "# Decision\n\n## Summary\nUse FTS fallback."
    assert calls[1][0] == "POST"
    assert calls[1][1] == "http://localhost:8000/library/contexts/search"
    assert recall_body == {"query": "FTS fallback", "strategy": "FTS_ONLY", "limit": 5}
    assert json.loads(save_stdout.getvalue())["id"] == "ctx-1"
    assert json.loads(recall_stdout.getvalue())["context_pack"] == "# Pack"


def test_cli_context_save_defaults_to_agent_source_type(tmp_path) -> None:
    """CLI context saves are agent-authored unless an imported source is explicit."""
    content_file = tmp_path / "handoff.md"
    content_file.write_text("# Handoff\n\n## Summary\nReady.", encoding="utf-8")
    calls: list[RecordedCall] = []

    def fake_transport(
        method: str,
        url: str,
        body: bytes | None,
        headers: HttpHeaders,
        timeout: float,
    ) -> tuple[int, bytes]:
        calls.append((method, url, body, headers, timeout))
        return 201, json.dumps({"id": "ctx-1", "title": "Handoff"}).encode()

    exit_code = run(
        [
            "--json",
            "context",
            "save",
            "--title",
            "Handoff",
            "--content-file",
            str(content_file),
        ],
        transport=fake_transport,
        stdout=io.StringIO(),
    )

    request_body = json.loads((calls[0][2] or b"{}").decode())
    assert exit_code == 0
    assert request_body["source_type"] == "AGENT"


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
            return 200, json.dumps({"fts": "HEALTHY", "vector": "DEGRADED"}).encode()
        return 200, json.dumps([{"id": "chunk-1", "context_id": "ctx-1"}]).encode()

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
    assert calls[0][1] == "http://localhost:8000/library/contexts/rag/status"
    assert calls[1][1] == "http://localhost:8000/library/contexts/ctx-1/chunks"
    assert "chunk-1" in stdout.getvalue()


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

    payload = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert payload["dry_run"] is True
    assert payload["hermes_home"] == str(hermes_home)
    assert payload["mcp_config"]["mcpServers"]["alexandria"]["args"] == [
        "mcp",
        "serve",
    ]
    assert "alexandria-hermes/prompts/capture-context.md" in payload["planned_files"]
    assert not (hermes_home / "alexandria-hermes").exists()


def test_hermes_json_output_redacts_mcp_api_token(tmp_path) -> None:
    """Hermes JSON output should never echo API tokens from flags or env."""
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
            "--api-token",
            "secret-token",
            "--dry-run",
        ],
        stdout=stdout,
    )

    output = stdout.getvalue()
    payload = json.loads(output)
    assert exit_code == 0
    assert "secret-token" not in output
    assert (
        payload["mcp_config"]["mcpServers"]["alexandria"]["env"]["ALEXANDRIA_API_TOKEN"]
        == "<REDACTED>"
    )


def test_hermes_install_mcp_uses_api_env_defaults(monkeypatch, tmp_path) -> None:
    """Hermes install-mcp preserves API URL and token environment defaults."""
    monkeypatch.setenv("ALEXANDRIA_API_URL", "http://env-backend:8000")
    monkeypatch.setenv("ALEXANDRIA_API_TOKEN", "env-secret-token")
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
    payload = json.loads(output)
    env = payload["mcp_config"]["mcpServers"]["alexandria"]["env"]
    assert exit_code == 0
    assert env["ALEXANDRIA_API_URL"] == "http://env-backend:8000"
    assert env["ALEXANDRIA_API_TOKEN"] == "<REDACTED>"
    assert "env-secret-token" not in output


def test_hermes_install_prompts_skips_existing_file_without_overwrite(tmp_path) -> None:
    """Hermes onboarding never overwrites existing files by default."""
    hermes_home = tmp_path / "hermes"
    existing = hermes_home / "alexandria-hermes" / "prompts" / "save-context.md"
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

    payload = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert existing.read_text(encoding="utf-8") == "custom"
    assert "alexandria-hermes/prompts/save-context.md" in payload["skipped"]
    assert "alexandria-hermes/prompts/capture-context.md" in payload["written"]


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

    payload = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert "alexandria-hermes/mcp-config.json" in payload["written"]
    assert payload["backups"] == ["alexandria-hermes/mcp-config.json.bak"]
    assert (config.parent / "mcp-config.json.bak").read_text(encoding="utf-8") == (
        '{"old": true}'
    )
    assert (
        json.loads(config.read_text(encoding="utf-8"))["mcpServers"]["alexandria"][
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
