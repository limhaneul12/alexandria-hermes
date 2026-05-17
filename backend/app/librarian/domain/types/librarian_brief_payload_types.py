"""Typed payload contracts for librarian brief packets."""

from __future__ import annotations

from typing_extensions import TypedDict


class SourceRefPayload(TypedDict, closed=True):
    """Public source reference payload."""

    source_type: str
    source_id: str
    title: str
    detail_path: str
    preview: str | None


class BudgetPolicyPayload(TypedDict, closed=True):
    """Public budget policy payload."""

    max_input_chars: int
    max_source_refs: int
    max_preview_chars: int


class ContextPackCompactPayload(TypedDict, closed=True):
    """Public compact context packet payload."""

    markdown_body: str
    source_refs: list[SourceRefPayload]


class LibrarianBriefPayload(TypedDict, closed=True):
    """Public compiled librarian brief payload."""

    prompt: str
    project: str | None
    packet_markdown: str
    source_refs: list[SourceRefPayload]
    budget_policy: BudgetPolicyPayload
