"""Search planning helpers for Obsidian librarian recall."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final

from app.obsidian.domain.contracts.obsidian_contracts import ObsidianLibrarianAsk
from app.obsidian.domain.event_enum.obsidian_enums import (
    AlexandriaNoteType,
    ObsidianLibrarianStopToken,
)
from app.shared.search.retrieval_query_variants import focused_query_variants

MAX_LIBRARIAN_QUERY_VARIANTS: Final[int] = 16
MAX_LIBRARIAN_SEARCH_LIMIT: Final[int] = 50
DEFAULT_LIBRARIAN_EXCLUDED_TYPES: Final[tuple[AlexandriaNoteType, ...]] = (
    AlexandriaNoteType.LIBRARIAN_CHAT,
)

_STOP_TOKENS: Final[frozenset[str]] = frozenset(
    token.value for token in ObsidianLibrarianStopToken
)


def librarian_query_text(payload: ObsidianLibrarianAsk) -> str:
    """Return the source-retrieval text for one librarian ask.

    Args:
        payload: Librarian ask command.

    Returns:
        Query text with the optional selection appended.
    """
    return "\n".join(
        part
        for part in [payload.query, payload.selection]
        if part is not None and part.strip()
    )


def librarian_query_variants(query: str) -> tuple[str, ...]:
    """Build focused recall queries from a possibly long instruction prompt.

    Args:
        query: User query text.

    Returns:
        Ordered query variants from broad to focused.
    """
    return focused_query_variants(
        query,
        stop_tokens=_STOP_TOKENS,
        max_variants=MAX_LIBRARIAN_QUERY_VARIANTS,
    )


def librarian_search_limit(source_ref_limit: int) -> int:
    """Return the per-query retrieval limit used before note de-duplication.

    Args:
        source_ref_limit: Requested unique source reference limit.

    Returns:
        Bounded per-query limit.
    """
    return min(MAX_LIBRARIAN_SEARCH_LIMIT, max(source_ref_limit * 3, source_ref_limit))


def librarian_type_filters(
    preferred_types: Iterable[AlexandriaNoteType],
) -> tuple[AlexandriaNoteType, ...]:
    """Return de-duplicated preferred librarian source types.

    Args:
        preferred_types: Caller-selected type filters.

    Returns:
        Type filters in caller order.
    """
    return tuple(dict.fromkeys(preferred_types))


def librarian_excluded_types(
    preferred_types: Iterable[AlexandriaNoteType],
) -> tuple[AlexandriaNoteType, ...]:
    """Return default exclusions for whole-vault librarian source search.

    Args:
        preferred_types: Caller-selected type filters.

    Returns:
        Note types to omit from whole-vault librarian retrieval.
    """
    if tuple(preferred_types):
        return ()
    return DEFAULT_LIBRARIAN_EXCLUDED_TYPES
