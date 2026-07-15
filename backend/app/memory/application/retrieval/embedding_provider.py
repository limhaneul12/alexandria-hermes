"""Local embedding provider contracts and lightweight test provider."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from json import dumps

from app.shared.types.extra_types import JSONObject

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_EMBEDDING_DIMENSIONS = 384


@dataclass(frozen=True, slots=True)
class EmbeddingFingerprint:
    """Stable identity for one embedding generation strategy."""

    provider: str
    model: str
    provider_version: str
    pooling_mode: str
    normalize: bool
    dimensions: int

    def identity_payload(self) -> JSONObject:
        """Return the timestamp-free identity payload.

        Returns:
            JSON-compatible embedding identity metadata.
        """
        return {
            "provider": self.provider,
            "model": self.model,
            "provider_version": self.provider_version,
            "pooling_mode": self.pooling_mode,
            "normalize": self.normalize,
            "dimensions": self.dimensions,
        }

    def key(self) -> str:
        """Return a deterministic key for equality comparisons.

        Returns:
            Stable JSON key excluding generated/index timestamps.
        """
        return dumps(
            self.identity_payload(),
            sort_keys=True,
            separators=(",", ":"),
        )

    def snapshot_payload(self, *, indexed_at: datetime) -> JSONObject:
        """Return persisted fingerprint metadata for one generated embedding.

        Args:
            indexed_at: Timestamp when the embedding was generated and stored.

        Returns:
            JSON-compatible fingerprint snapshot.
        """
        payload = self.identity_payload()
        timestamp = indexed_at.isoformat()
        payload["generated_at"] = timestamp
        payload["indexed_at"] = timestamp
        return payload


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

    @property
    def provider_version(self) -> str:
        """Return embedding implementation version.

        Returns:
            Provider library or test implementation version.
        """
        return "unknown"

    @property
    def pooling_mode(self) -> str:
        """Return document/query pooling mode.

        Returns:
            Stable pooling identifier.
        """
        return "default"

    @property
    def normalize(self) -> bool:
        """Return whether embeddings are normalized before storage.

        Returns:
            True when the provider stores normalized vectors.
        """
        return True

    def fingerprint(self) -> EmbeddingFingerprint:
        """Return the current embedding generation fingerprint.

        Returns:
            Stable fingerprint for mismatch detection.
        """
        return EmbeddingFingerprint(
            provider=self.provider_name,
            model=self.model_name,
            provider_version=self.provider_version,
            pooling_mode=self.pooling_mode,
            normalize=self.normalize,
            dimensions=self.dimensions,
        )

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
