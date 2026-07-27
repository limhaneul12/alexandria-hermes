"""FastEmbed provider compatibility tests."""

from __future__ import annotations

import sys
import warnings
from collections.abc import Iterable
from types import ModuleType

import pytest
from app.memory.application.retrieval.embedding_contract import (
    DEFAULT_EMBEDDING_MODEL,
)
from app.memory.application.retrieval.fastembed_provider import (
    FastEmbedEmbeddingProvider,
)

_MEAN_POOLING_ADVISORY = (
    "The model sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 "
    "now uses mean pooling instead of CLS embedding. In order to preserve the "
    "previous behaviour, consider either pinning fastembed version to 0.5.1 or "
    "using `add_custom_model` functionality."
)


class _AdvisoryTextEmbedding:
    """FastEmbed stand-in that emits the upstream pooling advisory."""

    def __init__(self, *, model_name: str, cache_dir: str | None = None) -> None:
        self.model_name = model_name
        self.cache_dir = cache_dir
        warnings.warn(_MEAN_POOLING_ADVISORY, UserWarning, stacklevel=2)

    def embed(self, texts: list[str]) -> Iterable[list[float]]:
        return ([float(len(text))] for text in texts)


class _UnexpectedWarningTextEmbedding(_AdvisoryTextEmbedding):
    """FastEmbed stand-in that emits a warning the provider must preserve."""

    def __init__(self, *, model_name: str, cache_dir: str | None = None) -> None:
        self.model_name = model_name
        self.cache_dir = cache_dir
        warnings.warn("unexpected FastEmbed warning", UserWarning, stacklevel=2)


def _install_fastembed_standin(
    monkeypatch: pytest.MonkeyPatch,
    text_embedding_type: type[_AdvisoryTextEmbedding],
) -> None:
    module = ModuleType("fastembed")
    module.TextEmbedding = text_embedding_type
    monkeypatch.setitem(sys.modules, "fastembed", module)


def test_default_model_accepts_mean_pooling_without_repeating_advisory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The selected mean-pooling behavior should not emit migration noise."""
    _install_fastembed_standin(monkeypatch, _AdvisoryTextEmbedding)
    provider = FastEmbedEmbeddingProvider(cache_dir="/tmp/fastembed-test-cache")

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        vector = provider.embed_query("alexandria")

    assert vector == [10.0]
    assert captured == []
    assert provider.pooling_mode == "fastembed-default"
    assert provider.fingerprint().model == DEFAULT_EMBEDDING_MODEL


def test_provider_does_not_hide_unrelated_fastembed_warnings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only the acknowledged upstream pooling advisory may be suppressed."""
    _install_fastembed_standin(monkeypatch, _UnexpectedWarningTextEmbedding)
    provider = FastEmbedEmbeddingProvider()

    with pytest.warns(UserWarning, match="unexpected FastEmbed warning"):
        provider.embed_query("alexandria")
