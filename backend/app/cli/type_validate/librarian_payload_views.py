"""Summary and status views over validated librarian CLI payloads."""

from __future__ import annotations

from app.cli.type_validate.librarian_payload_schemas import (
    LibrarianCheckSummaryPayload,
    NextActionPayload,
    ReviewQueueItemPayload,
    ReviewQueueSummaryPayload,
    validate_apply_status_payload,
    validate_combined_check_payload,
    validate_mcp_smoke_payload,
    validate_preflight_payload,
    validate_review_queue_payload,
)
from app.shared.types.extra_types import JSONValue


def review_queue_summary(payload: JSONValue) -> JSONValue:
    """Return a compact review-queue summary payload.

    Args:
        payload: Full review queue payload.

    Returns:
        JSON-compatible summary payload.
    """
    review_queue = validate_review_queue_payload(payload)
    top_item = review_queue.items[0] if review_queue.items else ReviewQueueItemPayload()
    summary = ReviewQueueSummaryPayload(
        total=review_queue.total
        if review_queue.total is not None
        else len(review_queue.items),
        auto_move_candidates=auto_move_candidate_count(review_queue.items),
        manual_review_required=manual_required_count(review_queue.items),
        top_item_id=top_item.id,
        top_item_path=top_item.path,
        top_item_reason=top_item.reason,
        top_item_action=top_item.recommended_action,
        top_item_confidence=top_item.confidence,
        top_item_requires_human_review=top_item.requires_human_review,
    )
    return summary.model_dump(mode="json")


def check_summary(mcp_smoke: JSONValue, preflight: JSONValue) -> JSONValue:
    """Return a compact combined MCP/preflight status payload.

    Args:
        mcp_smoke: MCP smoke-check payload.
        preflight: Librarian preflight payload.

    Returns:
        JSON-compatible summary payload.
    """
    smoke_payload = validate_mcp_smoke_payload(mcp_smoke)
    preflight_payload = validate_preflight_payload(preflight)
    readiness = preflight_payload.current_readiness()
    current_compact = readiness.current_memory_compact
    rag = readiness.rag
    review_queue = readiness.review_queue
    created_compact_id = (
        preflight_payload.created.id if preflight_payload.created is not None else None
    )
    next_action = (
        readiness.next_actions[0] if readiness.next_actions else NextActionPayload()
    )
    summary = LibrarianCheckSummaryPayload(
        ok=smoke_payload.ok and readiness.ready is True,
        mcp_url=smoke_payload.mcp_url,
        mcp_tool_count=smoke_payload.tool_count,
        mcp_required_tools_count=len(smoke_payload.required_tools),
        mcp_required_tools=smoke_payload.required_tools,
        mcp_missing_tools=smoke_payload.missing_tools,
        preflight_status=preflight_payload.status,
        refresh_required=preflight_payload.refresh_required,
        created=created_compact_id is not None,
        created_compact_id=created_compact_id,
        ready=readiness.ready,
        warnings=readiness.warnings,
        current_compact_id=current_compact.id,
        compact_age_days=current_compact.age_days,
        max_compact_age_days=current_compact.max_age_days,
        rag_fts=rag.fts,
        rag_vector=rag.vector,
        rag_embedding=rag.embedding,
        review_queue_total=review_queue.total,
        review_auto_move_candidates=review_queue.auto_move_candidates,
        review_manual_required=review_queue.manual_review_required,
        next_actions_count=len(readiness.next_actions),
        next_action=next_action.code,
        next_action_tool=next_action.tool,
    )
    return summary.model_dump(mode="json")


def confirmation_required(payload: JSONValue) -> bool:
    """Return whether the payload requires explicit apply confirmation.

    Args:
        payload: Candidate apply result payload.

    Returns:
        True when explicit apply confirmation is still required.
    """
    return validate_apply_status_payload(payload).status == "confirmation_required"


def auto_move_candidate_count(items: tuple[ReviewQueueItemPayload, ...]) -> int:
    """Count safe auto-move candidates in review queue items.

    Args:
        items: Validated review queue item objects.

    Returns:
        Number of queue items that can be moved automatically.
    """
    return sum(
        1
        for item in items
        if item.suggested_destination_path and item.requires_human_review is not True
    )


def manual_required_count(items: tuple[ReviewQueueItemPayload, ...]) -> int:
    """Count review queue items requiring manual librarian review.

    Args:
        items: Validated review queue item objects.

    Returns:
        Number of queue items requiring manual review.
    """
    return sum(1 for item in items if item.requires_human_review is True)


def check_ok(payload: JSONValue) -> bool:
    """Return whether a combined check payload is healthy.

    Args:
        payload: Candidate combined check payload.

    Returns:
        True when the combined check is healthy.
    """
    return validate_combined_check_payload(payload).ok is True


def mcp_smoke_ok(payload: JSONValue) -> bool:
    """Return whether an MCP smoke payload is healthy.

    Args:
        payload: Candidate MCP smoke payload.

    Returns:
        True when required MCP tools are exposed.
    """
    return validate_mcp_smoke_payload(payload).ok is True


def preflight_ready(payload: JSONValue) -> bool:
    """Return whether a preflight payload reports ready librarian state.

    Args:
        payload: Candidate preflight payload.

    Returns:
        True when librarian readiness reports ready state.
    """
    return validate_preflight_payload(payload).current_readiness().ready is True
