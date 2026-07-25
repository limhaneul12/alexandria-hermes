"""Stable public facade for embedding provider contracts and utilities."""

from __future__ import annotations

from app.memory.application.retrieval.embedding_contract import (
    DEFAULT_EMBEDDING_DIMENSIONS,
    DEFAULT_EMBEDDING_MODEL,
    EmbeddingProvider,
)
from app.memory.application.retrieval.embedding_fingerprint import (
    EmbeddingFingerprint,
)
from app.memory.application.retrieval.fake_embedding_provider import (
    FakeEmbeddingProvider,
)
from app.memory.application.retrieval.vector_math import cosine_similarity

__all__ = (
    "DEFAULT_EMBEDDING_DIMENSIONS",
    "DEFAULT_EMBEDDING_MODEL",
    "EmbeddingFingerprint",
    "EmbeddingProvider",
    "FakeEmbeddingProvider",
    "cosine_similarity",
)
