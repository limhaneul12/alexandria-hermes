"""Behavior tests for retrieval primitives."""

from __future__ import annotations

from app.memory.application.retrieval.chunker import chunk_markdown
from app.memory.application.retrieval.embedding_provider import FakeEmbeddingProvider


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
    assert [chunk.token_count for chunk in chunks] == [2, 4, 4]
    assert [chunk.content_hash for chunk in chunks] == [
        "b3297da392cbbb0893201b7cdc3121e35f2b34190868b94ff1d221ec394acec7",
        "6933f5bf2cb64cf2dfb59560a04dd92c07fcd95d63fa6031f9d69eb34aff029e",
        "9985ad61dbafad3c91f809680f1c42896a60162d8991419d2c9fcad8987f78c3",
    ]
    assert chunks[1].metadata == {"title": "Decision log", "heading": "Summary"}


def test_fake_embedding_provider_is_deterministic_without_model_downloads() -> None:
    """Tests should embed text without touching external model caches."""
    provider = FakeEmbeddingProvider()

    first = provider.embed_query("context recall")
    second = provider.embed_documents(["context recall"])[0]

    assert first == second
    assert len(first) == provider.dimensions
