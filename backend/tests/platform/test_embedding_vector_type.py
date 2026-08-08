"""PostgreSQL embedding vector storage type contracts."""

from __future__ import annotations

import pytest
from app.shared.infrastructure.embedding_vector_type import EmbeddingVectorType
from app.shared.types.embedding_types import normalize_embedding_vector
from sqlalchemy.dialects import postgresql, sqlite


def test_embedding_vector_type_compiles_to_pgvector() -> None:
    """Embedding columns should compile directly to the PostgreSQL vector type."""
    vector_type = EmbeddingVectorType(3)

    assert vector_type.compile(dialect=postgresql.dialect()) == "VECTOR(3)"


def test_embedding_vector_type_rejects_non_postgresql_dialects() -> None:
    """The runtime vector type must fail closed outside PostgreSQL/pgvector."""
    vector_type = EmbeddingVectorType(3)

    with pytest.raises(ValueError, match="requires PostgreSQL/pgvector"):
        vector_type.compile(dialect=sqlite.dialect())


def test_embedding_vector_type_passes_native_values_to_pgvector() -> None:
    """PostgreSQL binds should use native numeric vectors without JSON serialization."""
    vector_type = EmbeddingVectorType(3)
    vector = (0.25, -0.5, 1.0)

    stored = vector_type.process_bind_param(vector, postgresql.dialect())
    assert isinstance(stored, list)
    restored = vector_type.process_result_value(stored, postgresql.dialect())

    assert stored == [0.25, -0.5, 1.0]
    assert restored == vector


def test_embedding_vector_validation_rejects_non_finite_or_wrong_dimensions() -> None:
    """Invalid vectors should fail before reaching the PostgreSQL driver."""
    with pytest.raises(ValueError, match="non-finite"):
        normalize_embedding_vector((0.0, float("nan")))
    with pytest.raises(ValueError, match="unexpected dimensions"):
        normalize_embedding_vector((0.0,), expected_dimensions=2)
