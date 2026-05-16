"""SQLite vector serialization helpers."""

from __future__ import annotations

import math
from collections.abc import Iterable


def vector_to_sqlite_json(vector: Iterable[float]) -> str:
    """Serialize a finite float vector for sqlite-vec SQL functions.

    Args:
        vector: Ordered embedding values.

    Returns:
        str: JSON-compatible vector text accepted by sqlite-vec.

    Raises:
        ValueError: If the vector is empty or contains non-finite values.
    """
    values: list[str] = []
    for value in vector:
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError("Embedding vector contains a non-finite value")
        values.append(format(numeric, ".9g"))
    if not values:
        raise ValueError("Embedding vector is empty")
    serialized = f"[{','.join(values)}]"
    return serialized


def cosine_distance_to_score(distance: float) -> float:
    """Convert sqlite-vec cosine distance into a bounded similarity score.

    Args:
        distance: sqlite-vec cosine distance where identical vectors approach zero.

    Returns:
        float: Similarity score in the inclusive 0.0 to 1.0 range.
    """
    bounded_distance = min(max(distance, 0.0), 2.0)
    score = 1.0 - (bounded_distance / 2.0)
    return score
