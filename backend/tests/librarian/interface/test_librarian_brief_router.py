"""Librarian brief preview route tests."""

from __future__ import annotations

from app.main import app
from fastapi.testclient import TestClient


def test_librarian_brief_preview_returns_budgeted_packet() -> None:
    """Brief preview should expose compact packet text and lazy source refs."""
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/librarians/brief-preview",
            json={
                "prompt": "Need OAuth callback review skill",
                "project": "alexandria-hermes",
                "budget": {"max_input_chars": 600, "max_source_refs": 1},
                "context_compact": {
                    "markdown_body": "## Current compact\nUse callback verifier.",
                    "source_refs": [
                        {
                            "source_type": "MEMORY_COMPACT",
                            "source_id": "compact-1",
                            "title": "Current compact",
                            "detail_path": "/memory/compacts/compact-1",
                        }
                    ],
                },
                "source_refs": [
                    {
                        "source_type": "SKILL",
                        "source_id": "skill-1",
                        "title": "OAuth skill",
                        "detail_path": "obsidian://skills/oauth-skill",
                        "preview": "Markdown candidate preview; local vault full-loads it.",
                    }
                ],
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["project"] == "alexandria-hermes"
    assert len(body["packet_markdown"]) <= 600
    assert len(body["source_refs"]) == 1
    assert body["source_refs"][0]["source_id"] == "compact-1"
    assert "# Librarian Knowledge Packet" in body["packet_markdown"]
