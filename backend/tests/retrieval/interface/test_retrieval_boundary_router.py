"""Retrieval role boundary route tests."""

from __future__ import annotations

from app.main import app
from fastapi.testclient import TestClient


def test_retrieval_modes_are_explicit_and_separate_synthesis_from_search() -> None:
    """Retrieval mode API should make candidate search/full-load/RAG roles visible."""
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/retrieval/boundary/modes")

    body = response.json()
    modes = {item["mode"]: item for item in body}
    assert response.status_code == 200
    assert {
        "CONTEXT_RECALL",
        "CONTEXT_RAG_SYNTHESIS",
        "LIBRARY_CANDIDATE_SEARCH",
        "SELECTED_ITEM_FULL_LOAD",
        "LIBRARIAN_SYNTHESIS",
    } <= set(modes)
    assert modes["LIBRARY_CANDIDATE_SEARCH"]["returns_full_content"] is False
    assert modes["SELECTED_ITEM_FULL_LOAD"]["returns_full_content"] is True
    assert modes["CONTEXT_RAG_SYNTHESIS"]["uses_librarian"] is False
    assert modes["LIBRARIAN_SYNTHESIS"]["uses_librarian"] is True
