"""Markdown chunking for Context Vault retrieval."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.memory.domain.types.context_payload_types import ContextMetadataPayload
from app.shared.utils.text_metrics import count_word_tokens, sha256_text_hexdigest

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class MarkdownChunk:
    """One chunk produced from Markdown context content."""

    chunk_index: int
    heading: str | None
    content: str
    token_count: int
    content_hash: str
    metadata: ContextMetadataPayload


def _split_large_section(section: str, max_chars: int) -> list[str]:
    if len(section) <= max_chars:
        return [section]
    paragraphs = [
        paragraph.strip() for paragraph in section.split("\n\n") if paragraph.strip()
    ]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 2 > max_chars:
            chunks.append(current.strip())
            current = paragraph
        elif current:
            current = f"{current}\n\n{paragraph}"
        else:
            current = paragraph
    if current:
        chunks.append(current.strip())
    return chunks or [section[:max_chars]]


def chunk_markdown(
    title: str, content: str, max_chars: int = 1400
) -> list[MarkdownChunk]:
    """Split Markdown content into deterministic retrieval chunks.

    Args:
        title: Context title used as fallback heading.
        content: Markdown or text body.
        max_chars: Soft maximum characters per chunk.

    Returns:
        Ordered chunks with hashes and token counts.
    """
    normalized = content.strip()
    if not normalized:
        normalized = title.strip()

    matches = list(HEADING_PATTERN.finditer(normalized))
    sections: list[tuple[str | None, str]] = []
    if not matches:
        sections.append((title, normalized))
    else:
        if matches[0].start() > 0:
            sections.append((title, normalized[: matches[0].start()].strip()))
        for index, match in enumerate(matches):
            start = match.start()
            end = (
                matches[index + 1].start()
                if index + 1 < len(matches)
                else len(normalized)
            )
            heading = match.group(2).strip()
            sections.append((heading, normalized[start:end].strip()))

    chunks: list[MarkdownChunk] = []
    for heading, section in sections:
        if not section:
            continue
        for part in _split_large_section(section, max_chars):
            metadata: ContextMetadataPayload = {
                "title": title,
                "heading": heading or title,
            }
            chunks.append(
                MarkdownChunk(
                    chunk_index=len(chunks),
                    heading=heading,
                    content=part,
                    token_count=count_word_tokens(part),
                    content_hash=sha256_text_hexdigest(part),
                    metadata=metadata,
                )
            )
    return chunks
