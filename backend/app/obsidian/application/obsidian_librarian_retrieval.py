"""Search planning helpers for Obsidian librarian recall."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Final

from app.obsidian.domain.contracts.obsidian_contracts import ObsidianLibrarianAsk
from app.obsidian.domain.event_enum.obsidian_enums import AlexandriaNoteType
from app.shared.utils.text_metrics import extract_word_tokens

MAX_LIBRARIAN_QUERY_VARIANTS: Final[int] = 16
MAX_LIBRARIAN_SEARCH_LIMIT: Final[int] = 50
DEFAULT_LIBRARIAN_EXCLUDED_TYPES: Final[tuple[AlexandriaNoteType, ...]] = (
    AlexandriaNoteType.LIBRARIAN_CHAT,
)

_QUERY_SEGMENT_SPLIT_RE: Final[re.Pattern[str]] = re.compile(r"[,;\n]+")
_STOP_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "a",
        "about",
        "an",
        "and",
        "artifact",
        "artifacts",
        "by",
        "concrete",
        "decision",
        "decisions",
        "exclusion",
        "find",
        "for",
        "from",
        "how",
        "in",
        "intent",
        "is",
        "location",
        "locations",
        "note",
        "notes",
        "of",
        "on",
        "only",
        "or",
        "please",
        "point",
        "points",
        "prior",
        "recover",
        "return",
        "show",
        "source",
        "sources",
        "that",
        "the",
        "these",
        "this",
        "those",
        "to",
        "was",
        "were",
        "what",
        "when",
        "where",
        "why",
        "with",
    }
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
    variants: list[str] = []
    _append_variant(variants, query.strip())
    for segment in _QUERY_SEGMENT_SPLIT_RE.split(query):
        tokens = _meaningful_tokens(segment)
        _append_token_variant(variants, tokens)
        if len(tokens) > 4:
            _append_token_variant(variants, tokens[-4:])
        if len(tokens) > 3:
            _append_token_variant(variants, tokens[-3:])
        if len(variants) >= MAX_LIBRARIAN_QUERY_VARIANTS:
            break
    return tuple(variants[:MAX_LIBRARIAN_QUERY_VARIANTS])


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


def _meaningful_tokens(text: str) -> tuple[str, ...]:
    tokens = extract_word_tokens(text)
    return tuple(
        token
        for token in tokens
        if len(token) > 1 and token.casefold() not in _STOP_TOKENS
    )


def _append_token_variant(variants: list[str], tokens: tuple[str, ...]) -> None:
    if not tokens:
        return
    _append_variant(variants, " ".join(tokens))


def _append_variant(variants: list[str], query: str) -> None:
    normalized = " ".join(query.split())
    if not normalized:
        return
    if normalized in variants:
        return
    variants.append(normalized)
