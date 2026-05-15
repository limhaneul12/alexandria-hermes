"""FastEmbed local embedding provider."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from app.library.application.retrieval.embedding_provider import (
    DEFAULT_EMBEDDING_DIMENSIONS,
    DEFAULT_EMBEDDING_MODEL,
    EmbeddingProvider,
)

if TYPE_CHECKING:
    from fastembed import TextEmbedding


class FastEmbedEmbeddingProvider(EmbeddingProvider):
    """Lazy FastEmbed wrapper that does not download models until used."""

    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS,
        cache_dir: str | None = None,
    ) -> None:
        """Initialize provider configuration.

        Args:
            model_name: FastEmbed-supported model name.
            dimensions: Expected embedding dimensions.
            cache_dir: Optional local model cache directory.
        """
        self._model_name = model_name
        self._dimensions = dimensions
        self._cache_dir = cache_dir
        self._model: TextEmbedding | None = None

    @property
    def provider_name(self) -> str:
        """Return provider identifier.

        Returns:
            Stable provider name.
        """
        provider_name = "FASTEMBED_LOCAL"
        return provider_name

    @property
    def model_name(self) -> str:
        """Return FastEmbed model name.

        Returns:
            Local FastEmbed model identifier.
        """
        model_name = self._model_name
        return model_name

    @property
    def dimensions(self) -> int:
        """Return configured vector dimensions.

        Returns:
            Embedding vector size.
        """
        dimensions = self._dimensions
        return dimensions

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed document chunks with FastEmbed.

        Args:
            texts: Ordered document texts.

        Returns:
            One embedding vector per input text.
        """
        vectors = [
            list(vector) for vector in self._embedding_model().embed(list(texts))
        ]
        return vectors

    def embed_query(self, text: str) -> list[float]:
        """Embed one query with FastEmbed.

        Args:
            text: Query text.

        Returns:
            Query embedding vector.
        """
        vector = self.embed_documents([text])[0]
        return vector

    def _embedding_model(self) -> TextEmbedding:
        if self._model is None:
            from fastembed import TextEmbedding

            if self._cache_dir is None:
                self._model = TextEmbedding(model_name=self._model_name)
            else:
                self._model = TextEmbedding(
                    model_name=self._model_name,
                    cache_dir=self._cache_dir,
                )
        model = self._model
        return model
