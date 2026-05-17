"""Knowledge packet compiler behavior tests."""

from __future__ import annotations

from app.librarian.application.knowledge_packet_compiler import KnowledgePacketCompiler
from app.librarian.domain.entities.budget_policy import BudgetPolicy
from app.librarian.domain.entities.context_pack_compact import ContextPackCompact
from app.librarian.domain.entities.source_ref import SourceRef, SourceRefType


def _ref(source_id: str, *, preview: str = "preview") -> SourceRef:
    return SourceRef(
        source_type=SourceRefType.LIBRARY_ITEM,
        source_id=source_id,
        title=f"Item {source_id}",
        detail_path=f"/library/items/{source_id}",
        preview=preview,
    )


def test_compiler_caps_deduplicates_and_budgets_source_refs() -> None:
    """Compiler should emit a bounded packet with unique lazy-load refs."""
    compiler = KnowledgePacketCompiler()
    policy = BudgetPolicy(max_input_chars=420, max_source_refs=2, max_preview_chars=40)
    compact = ContextPackCompact(
        markdown_body="## Current compact\n" + "A" * 300,
        source_refs=(
            SourceRef(
                source_type=SourceRefType.MEMORY_COMPACT,
                source_id="compact-1",
                title="Current memory compact",
                detail_path="/memory/compacts/compact-1",
                preview="Prior decisions",
            ),
        ),
    )

    brief = compiler.compile(
        prompt="Find OAuth callback review evidence",
        project="alexandria-hermes",
        budget_policy=policy,
        context_compact=compact,
        source_refs=[_ref("skill-1"), _ref("skill-1"), _ref("prompt-1")],
    )

    assert len(brief.source_refs) == 2
    assert [ref.source_id for ref in brief.source_refs] == ["compact-1", "skill-1"]
    assert len(brief.packet_markdown) <= policy.max_input_chars
    assert "# Librarian Knowledge Packet" in brief.packet_markdown
    assert "Selected full-load" in brief.packet_markdown


def test_compiler_prefers_compact_context_over_raw_memory_style_inputs() -> None:
    """Current memory compact should be included before candidate previews."""
    compiler = KnowledgePacketCompiler()

    brief = compiler.compile(
        prompt="Summarize old memory",
        project=None,
        budget_policy=BudgetPolicy(max_input_chars=2000, max_source_refs=5),
        context_compact=ContextPackCompact(
            markdown_body="## Durable compact\nOld memory is already summarized.",
            source_refs=(),
        ),
        source_refs=[_ref("skill-1", preview="full body should not be loaded here")],
    )

    compact_index = brief.packet_markdown.index("Durable compact")
    refs_index = brief.packet_markdown.index("Source references")
    assert compact_index < refs_index
    assert "full body should not be loaded here" in brief.packet_markdown
