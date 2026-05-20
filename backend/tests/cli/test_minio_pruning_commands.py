"""Contracts proving the CLI no longer exposes MINIO sync commands."""

from __future__ import annotations

import io
from collections.abc import Callable

from app.cli import HttpHeaders, run
from app.shared.serialization.orjson_codec import dumps_json

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
        response = dumps_json(response_payload)
        return 200, response

    return fake_transport, calls


def test_cli_minio_command_is_not_registered() -> None:
    """The local CLI must not keep the removed object-storage import group."""
    transport, calls = _transport({"unexpected": True})
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = run(
        ["minio", "scan"], transport=transport, stdout=stdout, stderr=stderr
    )

    assert exit_code != 0
    assert calls == []
    assert "minio" in stderr.getvalue()
