"""Pydantic schemas for librarian brief preview endpoints."""

from __future__ import annotations

from pydantic import Field

from app.librarian.domain.entities.budget_policy import BudgetPolicy
from app.librarian.domain.entities.context_pack_compact import ContextPackCompact
from app.librarian.domain.entities.source_ref import SourceRef, SourceRefType
from app.shared.schemas.common_schemas import StrictSchemaModel


class SourceRefSchema(StrictSchemaModel):
    """I/O schema for a lazy-load source reference."""

    source_type: SourceRefType
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    detail_path: str = Field(min_length=1)
    preview: str | None = None

    def to_entity(self) -> SourceRef:
        """Convert schema to domain entity.

        Returns:
            Source reference domain entity.
        """
        return SourceRef(
            source_type=self.source_type,
            source_id=self.source_id,
            title=self.title,
            detail_path=self.detail_path,
            preview=self.preview,
        )


class BudgetPolicySchema(StrictSchemaModel):
    """I/O schema for packet budget policy."""

    max_input_chars: int = Field(default=12_000, ge=1)
    max_source_refs: int = Field(default=20, ge=1, le=100)
    max_preview_chars: int = Field(default=800, ge=1)

    def to_entity(self) -> BudgetPolicy:
        """Convert schema to domain entity.

        Returns:
            Budget policy domain entity.
        """
        return BudgetPolicy(
            max_input_chars=self.max_input_chars,
            max_source_refs=self.max_source_refs,
            max_preview_chars=self.max_preview_chars,
        )


class ContextPackCompactSchema(StrictSchemaModel):
    """I/O schema for compact context supplied to the compiler."""

    markdown_body: str = Field(min_length=1)
    source_refs: list[SourceRefSchema] = Field(default_factory=list)

    def to_entity(self) -> ContextPackCompact:
        """Convert schema to domain entity.

        Returns:
            Context-pack compact domain entity.
        """
        return ContextPackCompact(
            markdown_body=self.markdown_body,
            source_refs=tuple(
                source_ref.to_entity() for source_ref in self.source_refs
            ),
        )


class LibrarianBriefPreviewRequest(StrictSchemaModel):
    """Request to compile a preview knowledge packet."""

    prompt: str = Field(min_length=1)
    project: str | None = None
    budget: BudgetPolicySchema = Field(default_factory=BudgetPolicySchema)
    context_compact: ContextPackCompactSchema | None = None
    source_refs: list[SourceRefSchema] = Field(default_factory=list)


class LibrarianBriefPreviewResponse(StrictSchemaModel):
    """Compiled librarian brief preview response."""

    prompt: str
    project: str | None
    packet_markdown: str
    source_refs: list[SourceRefSchema]
    budget_policy: BudgetPolicySchema
