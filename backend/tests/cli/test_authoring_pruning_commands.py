"""CLI pruning contracts for removed human-authoring commands."""

from __future__ import annotations

import io
from collections.abc import Callable

import pytest
from app.cli import HttpHeaders, run
from app.shared.serialization.orjson_codec import dumps_json

RecordedCall = tuple[str, str, bytes | None, HttpHeaders, float]


def _transport() -> tuple[Callable[..., tuple[int, bytes]], list[RecordedCall]]:
    calls: list[RecordedCall] = []

    def fake_transport(
        method: str,
        url: str,
        body: bytes | None,
        headers: HttpHeaders,
        timeout: float,
    ) -> tuple[int, bytes]:
        calls.append((method, url, body, headers, timeout))
        return 200, dumps_json({"unexpected": True})

    return fake_transport, calls


@pytest.mark.parametrize(
    "argv",
    [
        [
            "skills",
            "create",
            "--title",
            "FastAPI skill",
            "--purpose",
            "Teach agent testing",
            "--content",
            "Use dependency overrides.",
        ],
        [
            "prompts",
            "create",
            "--title",
            "Review prompt",
            "--content",
            "Review this diff: {{diff}}",
        ],
        [
            "context",
            "lint",
            "handoff.md",
            "--title",
            "Handoff",
        ],
        [
            "context",
            "save",
            "--title",
            "Handoff",
            "--content",
            "# Handoff",
        ],
    ],
)
def test_removed_authoring_cli_commands_do_not_issue_http_requests(
    argv: list[str],
) -> None:
    """Human authoring/review commands should be removed before hitting HTTP."""
    transport, calls = _transport()
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = run(argv, transport=transport, stdout=stdout, stderr=stderr)

    assert exit_code != 0
    assert calls == []
