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
