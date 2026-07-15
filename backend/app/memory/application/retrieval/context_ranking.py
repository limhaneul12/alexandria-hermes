"""Context retrieval ranking helpers."""

from __future__ import annotations

from app.memory.domain.entities.context_read_models import ContextSearchMatch


def merge_hybrid_matches(
    *,
    fts_matches: list[ContextSearchMatch],
    vector_matches: list[ContextSearchMatch],
    limit: int,
) -> list[ContextSearchMatch]:
    """Merge FTS and vector matches using additive hybrid scoring.

    Args:
        fts_matches: Ranked FTS matches.
        vector_matches: Ranked vector matches.
        limit: Maximum returned matches.

    Returns:
        list[ContextSearchMatch]: Hybrid-ranked matches.
    """
    matches_by_chunk: dict[str, ContextSearchMatch] = {}
    for match in fts_matches:
        matches_by_chunk[match.chunk.id] = match

    for vector_match in vector_matches:
        existing = matches_by_chunk.get(vector_match.chunk.id)
        if existing is None:
            matches_by_chunk[vector_match.chunk.id] = vector_match
            continue
        fts_score = existing.fts_score or 0.0
        vector_score = vector_match.vector_score or 0.0
        matches_by_chunk[vector_match.chunk.id] = ContextSearchMatch(
            context=existing.context,
            chunk=existing.chunk,
            score=fts_score + vector_score,
            fts_score=existing.fts_score,
            vector_score=vector_match.vector_score,
            why_retrieved=(
                "Matched context chunk text with SQLite FTS5 and semantic "
                "embedding distance with sqlite-vec."
            ),
        )

    ranked = rank_best_matches_per_context(list(matches_by_chunk.values()), limit)
    return ranked


def rank_best_matches_per_context(
    matches: list[ContextSearchMatch],
    limit: int,
) -> list[ContextSearchMatch]:
    """Rank matches while keeping only the best chunk per context.

    Args:
        matches: Candidate matches from one or more retrieval sources.
        limit: Maximum returned contexts.

    Returns:
        Highest-scoring match per context, sorted by score.
    """
    best_by_context: dict[str, ContextSearchMatch] = {}
    for match in matches:
        existing = best_by_context.get(match.context.id)
        if existing is None or match.score > existing.score:
            best_by_context[match.context.id] = match
    return sorted(
        best_by_context.values(),
        key=lambda match: match.score,
        reverse=True,
    )[:limit]
