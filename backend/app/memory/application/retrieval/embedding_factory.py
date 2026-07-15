"""Embedding provider composition helpers."""

from __future__ import annotations

from typing import Literal

from app.memory.application.retrieval.embedding_provider import (
    DEFAULT_EMBEDDING_DIMENSIONS,
    DEFAULT_EMBEDDING_MODEL,
    EmbeddingProvider,
    FakeEmbeddingProvider,
)
from app.memory.application.retrieval.fastembed_provider import (
    FastEmbedEmbeddingProvider,
)

EmbeddingProviderName = Literal["fastembed", "fake-test", "disabled"]


def create_embedding_provider(
    *,
    vector_enabled: bool,
    provider_name: EmbeddingProviderName,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS,
    cache_dir: str | None = None,
) -> EmbeddingProvider | None:
    """Create the configured local embedding provider.

    Args:
        vector_enabled: Whether vector retrieval is enabled for the service.
        provider_name: Configured embedding provider identifier.
        model_name: Embedding model identifier.
        dimensions: Embedding vector dimension count.
        cache_dir: Optional model cache directory.

    Returns:
        EmbeddingProvider | None: Provider instance when vector recall can embed text.
    """
    if not vector_enabled or provider_name == "disabled":
        return None
    if provider_name == "fake-test":
        return FakeEmbeddingProvider(model_name=model_name, dimensions=dimensions)
    return FastEmbedEmbeddingProvider(
        model_name=model_name,
        dimensions=dimensions,
        cache_dir=cache_dir,
    )
