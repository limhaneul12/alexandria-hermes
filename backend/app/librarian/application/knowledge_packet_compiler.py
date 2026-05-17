"""Compile budgeted knowledge packets for librarian delegates."""

from __future__ import annotations

from collections.abc import Iterable

from app.librarian.domain.entities.budget_policy import BudgetPolicy
from app.librarian.domain.entities.context_pack_compact import ContextPackCompact
from app.librarian.domain.entities.librarian_brief import LibrarianBrief
from app.librarian.domain.entities.source_ref import SourceRef


class KnowledgePacketCompiler:
    """Build compact/source-ref packets instead of passing raw context."""

    def compile(
        self,
        *,
        prompt: str,
        project: str | None,
        budget_policy: BudgetPolicy,
        context_compact: ContextPackCompact | None = None,
        source_refs: Iterable[SourceRef] = (),
    ) -> LibrarianBrief:
        """Compile a packet for a librarian call.

        Args:
            prompt: User/Hermes request.
            project: Optional project scope.
            budget_policy: Packet budget.
            context_compact: Current durable memory compact, if available.
            source_refs: Candidate lazy-load references from search/retrieval.

        Returns:
            LibrarianBrief: Budgeted compact packet.
        """
        refs = _deduplicated_refs(context_compact, source_refs)
        selected_refs = tuple(refs[: budget_policy.max_source_refs])
        packet_markdown = _budgeted_markdown(
            prompt=prompt,
            project=project,
            budget_policy=budget_policy,
            context_compact=context_compact,
            source_refs=selected_refs,
        )
        return LibrarianBrief(
            prompt=prompt,
            project=project,
            packet_markdown=packet_markdown,
            source_refs=selected_refs,
            budget_policy=budget_policy,
        )


def _deduplicated_refs(
    context_compact: ContextPackCompact | None,
    source_refs: Iterable[SourceRef],
) -> list[SourceRef]:
    seen: set[tuple[str, str]] = set()
    refs: list[SourceRef] = []
    ordered_refs: list[SourceRef] = []
    if context_compact is not None:
        ordered_refs.extend(context_compact.source_refs)
    ordered_refs.extend(source_refs)
    for source_ref in ordered_refs:
        key = (source_ref.source_type.value, source_ref.source_id)
        if key in seen:
            continue
        seen.add(key)
        refs.append(source_ref)
    return refs


def _budgeted_markdown(
    *,
    prompt: str,
    project: str | None,
    budget_policy: BudgetPolicy,
    context_compact: ContextPackCompact | None,
    source_refs: tuple[SourceRef, ...],
) -> str:
    lines = [
        "# Librarian Knowledge Packet",
        "",
        "## Request",
        f"- project: {project or 'none'}",
        f"- prompt: {prompt.strip()}",
        "",
        "## Retrieval boundary",
        "- Use the compact packet and source refs first.",
        "- Do not assume broad search returned full source bodies.",
        "- Selected full-load is available through each source ref detail_path.",
        "",
    ]
    if context_compact is not None:
        lines.extend(
            [
                "## Current Memory Compact",
                _clip(
                    context_compact.markdown_body.strip(), budget_policy.max_input_chars
                ),
                "",
            ]
        )
    lines.extend(["## Source references", ""])
    if not source_refs:
        lines.append(
            "No source refs were supplied; ask Hermes to search or recall first."
        )
    for index, source_ref in enumerate(source_refs, start=1):
        lines.extend(
            [
                f"### {index}. {source_ref.title}",
                f"- type: {source_ref.source_type.value}",
                f"- id: {source_ref.source_id}",
                f"- detail_path: {source_ref.detail_path}",
            ]
        )
        if source_ref.preview:
            lines.append(
                f"- preview: {_clip(source_ref.preview, budget_policy.max_preview_chars)}"
            )
        lines.append("")
    return _clip("\n".join(lines).strip() + "\n", budget_policy.max_input_chars)


def _clip(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    if limit <= 1:
        return value[:limit]
    return value[: limit - 1].rstrip() + "…"
