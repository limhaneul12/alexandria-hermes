"""CLI Pydantic payload contract tests."""

from __future__ import annotations

from app.cli.type_validate.librarian_payload_views import (
    check_summary,
    preflight_ready,
    review_queue_summary,
)
from app.cli.type_validate.mcp_protocol_payload_contracts import mcp_tool_names


def test_review_queue_summary_uses_validated_items_when_payload_is_mixed() -> None:
    """Review queue summaries should ignore non-object list items safely."""
    payload = {
        "items": [
            "not-an-object",
            {
                "id": "ctx-1",
                "path": "Alexandria/_Inbox/Captured.md",
                "suggested_destination_path": "Alexandria/Contexts/Captured.md",
                "requires_human_review": False,
            },
            {"id": "manual", "requires_human_review": True},
        ]
    }

    assert review_queue_summary(payload) == {
        "total": 2,
        "auto_move_candidates": 1,
        "manual_review_required": 1,
        "top_item_id": "ctx-1",
        "top_item_path": "Alexandria/_Inbox/Captured.md",
        "top_item_reason": None,
        "top_item_action": None,
        "top_item_confidence": None,
        "top_item_requires_human_review": False,
    }


def test_check_summary_defaults_missing_nested_payloads_to_not_ready() -> None:
    """Check summaries should not treat absent readiness evidence as healthy."""
    summary = check_summary(
        mcp_smoke={"ok": True, "required_tools": ["tool-a"]},
        preflight={"status": "missing-readiness"},
    )

    assert summary["ok"] is False
    assert summary["ready"] is None
    assert summary["mcp_required_tools_count"] == 1
    assert summary["warnings"] == []
    assert summary["next_actions_count"] == 0


def test_preflight_ready_uses_post_refresh_readiness_before_direct_readiness() -> None:
    """Preflight readiness should prefer post-refresh evidence."""
    payload = {
        "readiness": {"ready": True},
        "post_refresh_readiness": {"ready": False},
    }

    assert preflight_ready(payload) is False


def test_mcp_tool_names_uses_validated_tool_objects_only() -> None:
    """MCP tools/list parsing should ignore malformed tool entries."""
    payload = {
        "result": {
            "tools": [
                {"name": "alexandria_librarian_readiness"},
                {"title": "missing name"},
                "not-an-object",
            ]
        }
    }

    assert mcp_tool_names(payload) == {"alexandria_librarian_readiness"}
