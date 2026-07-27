"""SQLite FTS5 relevance-score normalization."""

from __future__ import annotations


def sqlite_fts_rank_to_score(rank: float) -> float:
    """Convert SQLite FTS5 BM25 rank into a higher-is-better relevance score.

    SQLite FTS5 returns better BM25 matches as smaller rank values. Negating the
    rank preserves that ordering for application code that sorts scores in
    descending order.

    Args:
        rank: Raw SQLite FTS5 BM25 rank.

    Returns:
        Monotonic higher-is-better relevance score.
    """
    return -rank
