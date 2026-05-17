"""Retrieval role boundary enums."""

from __future__ import annotations

from enum import StrEnum


class RetrievalMode(StrEnum):
    """Explicit retrieval and synthesis roles."""

    CONTEXT_RECALL = "CONTEXT_RECALL"
    CONTEXT_RAG_SYNTHESIS = "CONTEXT_RAG_SYNTHESIS"
    LIBRARY_CANDIDATE_SEARCH = "LIBRARY_CANDIDATE_SEARCH"
    SELECTED_ITEM_FULL_LOAD = "SELECTED_ITEM_FULL_LOAD"
    LIBRARIAN_SYNTHESIS = "LIBRARIAN_SYNTHESIS"
