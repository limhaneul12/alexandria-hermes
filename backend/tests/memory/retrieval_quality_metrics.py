"""Deterministic metrics for golden Context retrieval cases."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class GoldenRetrievalResult:
    """Expected and observed canonical ids for one retrieval query."""

    query: str
    expected_context_ids: tuple[str, ...]
    retrieved_context_ids: tuple[str, ...]


def recall_at_k(results: tuple[GoldenRetrievalResult, ...], k: int) -> float:
    """Return the fraction of queries with an expected result in the top K."""
    if not results:
        return 0.0
    hits = sum(
        1
        for result in results
        if set(result.expected_context_ids) & set(result.retrieved_context_ids[:k])
    )
    return hits / len(results)


def mean_reciprocal_rank(results: tuple[GoldenRetrievalResult, ...]) -> float:
    """Return mean reciprocal rank for the first expected result per query."""
    if not results:
        return 0.0
    reciprocal_ranks: list[float] = []
    for result in results:
        expected_ids = set(result.expected_context_ids)
        rank = next(
            (
                index
                for index, context_id in enumerate(
                    result.retrieved_context_ids,
                    start=1,
                )
                if context_id in expected_ids
            ),
            None,
        )
        reciprocal_ranks.append(0.0 if rank is None else 1.0 / rank)
    return sum(reciprocal_ranks) / len(reciprocal_ranks)
