"""PostgreSQL full-text rank normalization helpers."""

from __future__ import annotations


def postgres_fts_rank_to_score(rank: float) -> float:
    """Convert a non-negative PostgreSQL text-search rank to a bounded score.

    Args:
        rank: Raw ``ts_rank_cd`` value where larger values are more relevant.

    Returns:
        Monotonic score in the inclusive 0.0 to 1.0 range.
    """
    bounded_rank = max(rank, 0.0)
    return bounded_rank / (1.0 + bounded_rank)
