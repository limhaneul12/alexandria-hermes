"""Behavior tests for Obsidian CLI commands."""

from __future__ import annotations

import io
from collections.abc import Callable
from pathlib import Path

from app.cli import HttpHeaders, run
from app.shared.serialization.orjson_codec import dumps_json, loads_json

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
        return 200, dumps_json(response_payload)

    return fake_transport, calls


def test_cli_obsidian_status_calls_backend_status() -> None:
    """Status command calls the Obsidian status endpoint."""
    transport, calls = _transport({"vault_exists": True})
    stdout = io.StringIO()

    exit_code = run(
        ["--json", "obsidian", "status"],
        transport=transport,
        stdout=stdout,
    )

    assert exit_code == 0
    assert calls[0][0] == "GET"
    assert calls[0][1] == "http://localhost:8000/obsidian/status"
    assert calls[0][2] is None
    assert loads_json(stdout.getvalue())["vault_exists"] is True


def test_cli_obsidian_search_posts_filters() -> None:
    """Search command forwards query, type, project, and tag filters."""
    transport, calls = _transport({"items": [], "total": 0})
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "obsidian",
            "search",
            "long memory",
            "--limit",
            "3",
            "--type",
            "context",
            "--project",
            "alexandria-hermes",
            "--tag",
            "memory",
        ],
        transport=transport,
        stdout=stdout,
    )

    request_body = loads_json((calls[0][2] or b"{}").decode())
    assert exit_code == 0
    assert calls[0][0] == "POST"
    assert calls[0][1] == "http://localhost:8000/obsidian/search"
    assert request_body == {
        "query": "long memory",
        "limit": 3,
        "tags": ["memory"],
        "alexandria_type": "context",
        "project": "alexandria-hermes",
    }


def test_cli_obsidian_related_reads_by_path() -> None:
    """Related command calls the graph related-notes endpoint."""
    transport, calls = _transport({"items": [], "total": 0})
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "obsidian",
            "related",
            "--path",
            "Alexandria/START_HERE.md",
            "--limit",
            "4",
        ],
        transport=transport,
        stdout=stdout,
    )

    assert exit_code == 0
    assert calls[0][0] == "GET"
    assert calls[0][1] == (
        "http://localhost:8000/obsidian/notes/by-path/related?"
        "path=Alexandria/START_HERE.md&limit=4"
    )


def test_cli_obsidian_save_reads_markdown_body(tmp_path: Path) -> None:
    """Save command reads Markdown body file and posts note metadata."""
    body_file = tmp_path / "body.md"
    body_file.write_text("# Durable Skill\n\nUse Obsidian.", encoding="utf-8")
    transport, calls = _transport({"id": "skill_1"})
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "obsidian",
            "save",
            "Durable Skill",
            "--body-file",
            str(body_file),
            "--type",
            "skill",
            "--id",
            "skill_1",
            "--path",
            "Alexandria/Skills/Durable Skill.md",
            "--tag",
            "skill",
            "--status",
            "draft",
            "--source",
            "migration",
            "--frontmatter-json",
            '{"skill_status":"draft"}',
        ],
        transport=transport,
        stdout=stdout,
    )

    request_body = loads_json((calls[0][2] or b"{}").decode())
    assert exit_code == 0
    assert calls[0][1] == "http://localhost:8000/obsidian/notes"
    assert request_body["body"] == "# Durable Skill\n\nUse Obsidian."
    assert request_body["alexandria_type"] == "skill"
    assert request_body["id"] == "skill_1"
    assert request_body["tags"] == ["skill"]
    assert request_body["status"] == "draft"
    assert request_body["source"] == "migration"
    assert request_body["frontmatter"] == {"skill_status": "draft"}


def test_cli_obsidian_capture_posts_canonical_artifact_defaults(
    tmp_path: Path,
) -> None:
    """Capture command writes typed frontmatter/tags for canonical artifacts."""
    body_file = tmp_path / "prompt.md"
    body_file.write_text("# Prompt\n\nReview release notes.", encoding="utf-8")
    transport, calls = _transport({"id": "prompt_release"})
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "obsidian",
            "capture",
            "Release Review Prompt",
            "--body-file",
            str(body_file),
            "--type",
            "prompt",
            "--id",
            "prompt_release",
            "--project",
            "alexandria-hermes",
            "--tag",
            "review",
            "--prompt-kind",
            "template",
        ],
        transport=transport,
        stdout=stdout,
    )

    request_body = loads_json((calls[0][2] or b"{}").decode())
    assert exit_code == 0
    assert calls[0][1] == "http://localhost:8000/obsidian/notes"
    assert request_body == {
        "title": "Release Review Prompt",
        "body": "# Prompt\n\nReview release notes.",
        "alexandria_type": "prompt",
        "tags": ["alexandria", "prompt", "template", "review"],
        "status": "draft",
        "source": "import",
        "frontmatter": {
            "artifact_kind": "prompt",
            "prompt_kind": "template",
        },
        "id": "prompt_release",
        "project": "alexandria-hermes",
    }


def test_cli_obsidian_capture_rejects_non_artifact_type(tmp_path: Path) -> None:
    """Capture should be limited to memory, skill, and prompt artifacts."""
    body_file = tmp_path / "context.md"
    body_file.write_text("# Context", encoding="utf-8")
    transport, calls = _transport({"id": "ctx"})
    stderr = io.StringIO()

    exit_code = run(
        [
            "--json",
            "obsidian",
            "capture",
            "Not Artifact",
            "--body-file",
            str(body_file),
            "--type",
            "context",
        ],
        transport=transport,
        stderr=stderr,
    )

    assert exit_code == 1
    assert calls == []
    assert "capture --type must be one of" in stderr.getvalue()


def test_cli_obsidian_ask_posts_librarian_context() -> None:
    """Ask command forwards active note context and transcript preference."""
    transport, calls = _transport({"answer_markdown": "ok"})
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "obsidian",
            "ask",
            "What should I remember?",
            "--active-note-path",
            "Alexandria/Contexts/Today.md",
            "--selection",
            "selected text",
            "--project",
            "alexandria-hermes",
            "--save-transcript",
        ],
        transport=transport,
        stdout=stdout,
    )

    request_body = loads_json((calls[0][2] or b"{}").decode())
    assert exit_code == 0
    assert calls[0][1] == "http://localhost:8000/obsidian/librarian/ask"
    assert request_body == {
        "query": "What should I remember?",
        "save_transcript": True,
        "active_note_path": "Alexandria/Contexts/Today.md",
        "selection": "selected text",
        "project": "alexandria-hermes",
    }


def test_cli_obsidian_ask_can_request_delegated_provider() -> None:
    """Ask command forwards provider/profile delegation hooks without tokens."""
    transport, calls = _transport({"answer_markdown": "ok"})
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "obsidian",
            "ask",
            "Need outside critic",
            "--delegate",
            "--provider-id",
            "codex-oauth",
            "--profile-id",
            "research-critic",
        ],
        transport=transport,
        stdout=stdout,
    )

    request_body = loads_json((calls[0][2] or b"{}").decode())
    assert exit_code == 0
    assert request_body == {
        "query": "Need outside critic",
        "save_transcript": False,
        "delegate_to_librarian": True,
        "provider_id": "codex-oauth",
        "profile_id": "research-critic",
    }
