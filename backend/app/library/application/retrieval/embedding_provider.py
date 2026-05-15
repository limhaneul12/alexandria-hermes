"""Local embedding provider contracts and lightweight test provider."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_EMBEDDING_DIMENSIONS = 384


class EmbeddingProvider(ABC):
    """Abstract contract for local text embedding providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider identifier.

        Returns:
            Stable provider name.
        """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return model identifier.

        Returns:
            Local embedding model name.
        """

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return vector dimensions.

        Returns:
            Embedding vector size.
        """

    @abstractmethod
    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed document chunks.

        Args:
            texts: Ordered document texts.

        Returns:
            One embedding vector per input text.
        """

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed one search query.

        Args:
            text: Query text.

        Returns:
            Query embedding vector.
        """


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic local provider for tests and offline fallback paths."""

    def __init__(
        self,
        model_name: str = "fake-local-embedding",
        dimensions: int = 8,
        provider_name: str = "FAKE_LOCAL",
    ) -> None:
        """Initialize deterministic provider settings.

        Args:
            model_name: Local fake model identifier.
            dimensions: Embedding vector size.
            provider_name: Local fake provider identifier.

        Returns:
            None.
        """
        self._model_name = model_name
        self._dimensions = dimensions
        self._provider_name = provider_name

    @property
    def provider_name(self) -> str:
        """Return provider identifier.

        Returns:
            Stable provider name.
        """
        provider_name = self._provider_name
        return provider_name

    @property
    def model_name(self) -> str:
        """Return model identifier.

        Returns:
            Fake model name.
        """
        model_name = self._model_name
        return model_name

    @property
    def dimensions(self) -> int:
        """Return vector dimensions.

        Returns:
            Fake vector size.
        """
        dimensions = self._dimensions
        return dimensions

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed document chunks deterministically without external downloads.

        Args:
            texts: Ordered document texts.

        Returns:
            One deterministic vector per text.
        """
        vectors = [self._embed(text) for text in texts]
        return vectors

    def embed_query(self, text: str) -> list[float]:
        """Embed one query deterministically.

        Args:
            text: Query text.

        Returns:
            Deterministic query vector.
        """
        vector = self._embed(text)
        return vector

    def _embed(self, text: str) -> list[float]:
        buckets = [0.0 for _ in range(self.dimensions)]
        for index, byte in enumerate(text.encode("utf-8")):
            buckets[index % self.dimensions] += float(byte) / 255.0
        magnitude = sum(value * value for value in buckets) ** 0.5 or 1.0
        return [value / magnitude for value in buckets]


def cosine_similarity(left: Iterable[float], right: Iterable[float]) -> float:
    """Return cosine similarity for two vectors.

    Args:
        left: First vector.
        right: Second vector.

    Returns:
        Cosine similarity in the inclusive range allowed by vector content.
    """
    left_values = list(left)
    right_values = list(right)
    if len(left_values) != len(right_values) or not left_values:
        return 0.0
    dot = sum(
        l_value * r_value
        for l_value, r_value in zip(left_values, right_values, strict=True)
    )
    left_norm = sum(value * value for value in left_values) ** 0.5
    right_norm = sum(value * value for value in right_values) ** 0.5
    denominator = left_norm * right_norm
    if denominator == 0:
        return 0.0
    similarity = dot / denominator
    return similarity
