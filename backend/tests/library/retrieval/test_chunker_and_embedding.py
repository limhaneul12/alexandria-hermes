"""Behavior tests for retrieval primitives."""

from __future__ import annotations

from app.retrieval.application.chunker import chunk_markdown
from app.retrieval.application.embedding_provider import FakeEmbeddingProvider


def test_markdown_chunker_keeps_heading_metadata_and_hashes() -> None:
    """Markdown chunks should retain heading context for recall explanations."""
    chunks = chunk_markdown(
        title="Decision log",
        content="""# Decision log

## Summary
Use local embeddings.

## Evidence
FastEmbed works locally.
""",
    )

    assert [chunk.heading for chunk in chunks] == [
        "Decision log",
        "Summary",
        "Evidence",
    ]
    assert all(chunk.content_hash for chunk in chunks)
    assert chunks[1].metadata == {"title": "Decision log", "heading": "Summary"}


def test_fake_embedding_provider_is_deterministic_without_model_downloads() -> None:
    """Tests should embed text without touching external model caches."""
    provider = FakeEmbeddingProvider()

    first = provider.embed_query("context recall")
    second = provider.embed_documents(["context recall"])[0]

    assert first == second
    assert len(first) == provider.dimensions
