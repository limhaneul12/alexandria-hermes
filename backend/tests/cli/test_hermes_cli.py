"""Behavior tests for the Hermes CLI HTTP client."""

from __future__ import annotations

import io
import json
from collections.abc import Callable

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
    assert "{list,get,create,delete}" in result.stdout


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
