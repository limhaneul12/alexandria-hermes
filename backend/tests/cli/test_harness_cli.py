"""Behavior tests for execution harness CLI commands."""

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


def test_cli_lists_harnesses_through_context_vault_route() -> None:
    """Harness list should use the Context Vault HARNESS management route."""
    transport, calls = _transport({"items": [], "total": 0})
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "harness",
            "list",
            "--project",
            "alexandria-hermes",
            "--scope",
            "PROJECT",
            "--source-agent",
            "Hermes",
            "--tag",
            "refactor",
            "--limit",
            "7",
            "--offset",
            "2",
            "--include-archived",
        ],
        transport=transport,
        stdout=stdout,
    )

    assert exit_code == 0
    assert calls[0][0] == "GET"
    assert calls[0][1] == (
        "http://localhost:8000/memory/contexts/harnesses?limit=7&offset=2"
        "&include_archived=true&project=alexandria-hermes&scope=PROJECT"
        "&source_agent=Hermes&tag=refactor"
    )
    assert loads_json(stdout.getvalue()) == {"items": [], "total": 0}


def test_cli_captures_harness_with_reusable_procedure() -> None:
    """Harness capture should submit structured procedure details."""
    transport, calls = _transport({"id": "ctx-1", "kind": "HARNESS"})
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "harness",
            "capture",
            "--task-goal",
            "Refactor CLI support",
            "--procedure",
            "Read rules, edit, and run make ci.",
            "--project",
            "alexandria-hermes",
            "--step",
            "Read backend rules",
            "--command",
            "make ci",
            "--test",
            "backend make ci",
            "--keyword",
            "cli-refactor",
            "--safety-note",
            "No destructive commands.",
        ],
        transport=transport,
        stdout=stdout,
    )

    body = loads_json(calls[0][2] or b"{}")
    assert exit_code == 0
    assert calls[0][0] == "POST"
    assert calls[0][1] == "http://localhost:8000/memory/contexts/harnesses/capture"
    assert body == {
        "task_goal": "Refactor CLI support",
        "reusable_procedure": "Read rules, edit, and run make ci.",
        "project": "alexandria-hermes",
        "scope": "PROJECT",
        "source_agent": "Hermes",
        "steps": ["Read backend rules"],
        "commands": ["make ci"],
        "tests": ["backend make ci"],
        "failures": [],
        "fixes": [],
        "artifacts": [],
        "recall_keywords": ["cli-refactor"],
        "safety_notes": ["No destructive commands."],
        "metadata": {},
    }
    assert loads_json(stdout.getvalue()) == {"id": "ctx-1", "kind": "HARNESS"}


def test_cli_checks_harness_from_procedure_file(tmp_path: Path) -> None:
    """Harness check should validate file-backed procedure content without saving."""
    procedure_path = tmp_path / "procedure.md"
    procedure_path.write_text("## Procedure\nRun the safe steps.\n", encoding="utf-8")
    transport, calls = _transport({"ok": True, "status": "SAVED"})
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "harness",
            "check",
            "--task-goal",
            "Validate a procedure",
            "--procedure-file",
            str(procedure_path),
        ],
        transport=transport,
        stdout=stdout,
    )

    body = loads_json(calls[0][2] or b"{}")
    assert exit_code == 0
    assert calls[0][0] == "POST"
    assert calls[0][1] == "http://localhost:8000/memory/contexts/harnesses/check"
    assert body["reusable_procedure"] == "## Procedure\nRun the safe steps."
    assert loads_json(stdout.getvalue()) == {"ok": True, "status": "SAVED"}


def test_cli_gets_and_archives_harness_by_encoded_id() -> None:
    """Harness get/archive should keep ids inside one URL path segment."""
    transport, calls = _transport({"id": "ctx/1", "kind": "HARNESS"})
    stdout = io.StringIO()

    get_exit = run(
        ["--json", "harness", "get", "ctx/1"],
        transport=transport,
        stdout=stdout,
    )
    archive_exit = run(
        ["--json", "harness", "archive", "ctx/1"],
        transport=transport,
        stdout=stdout,
    )

    assert get_exit == 0
    assert archive_exit == 0
    assert [(call[0], call[1]) for call in calls] == [
        ("GET", "http://localhost:8000/memory/contexts/harnesses/ctx%2F1"),
        ("POST", "http://localhost:8000/memory/contexts/harnesses/ctx%2F1/archive"),
    ]
