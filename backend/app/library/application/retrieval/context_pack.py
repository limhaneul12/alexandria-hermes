"""Context Pack builder for agent-facing RAG responses."""

from __future__ import annotations

from app.library.domain.entities.context_read_models import ContextSearchMatch


def build_context_pack(query: str, matches: list[ContextSearchMatch]) -> str:
    """Build a compact Markdown context pack from retrieval matches.

    Args:
        query: Search query text.
        matches: Retrieved context matches.

    Returns:
        Markdown Context Pack for agent prompts.
    """
    lines = ["# Alexandria Context Pack", "", f"Query: {query}", ""]
    for index, match in enumerate(matches, start=1):
        context = match.context
        chunk = match.chunk
        heading = f" — {chunk.heading}" if chunk.heading else ""
        lines.extend(
            [
                f"## {index}. {context.title}{heading}",
                f"- context_id: {context.id}",
                f"- chunk_id: {chunk.id}",
                f"- kind: {context.kind.value}",
                f"- project: {context.project or 'none'}",
                f"- score: {match.score:.4f}",
                f"- why: {match.why_retrieved}",
                "",
                chunk.content.strip(),
                "",
            ]
        )
    context_pack = "\n".join(lines).strip() + "\n"
    return context_pack
