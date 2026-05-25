"""HTTP schemas for Obsidian vault operations."""

from __future__ import annotations

from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianLibrarianAsk,
    ObsidianSaveNote,
    ObsidianSearchQuery,
)
from app.obsidian.domain.entities.obsidian_note import (
    ObsidianNote,
    ObsidianReindexResult,
    ObsidianSearchHit,
    ObsidianVaultStatus,
)
from app.obsidian.domain.event_enum.obsidian_enums import (
    AlexandriaNoteType,
    ObsidianIndexStatus,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.schemas.datetime_schemas import AwareTimestamp
from app.shared.types.extra_types import JSONObject
from pydantic import Field


class ObsidianStatusResponse(StrictSchemaModel):
    """Current Obsidian vault/index status."""

    vault_path: str
    alexandria_root: str
    vault_exists: bool
    alexandria_root_exists: bool
    indexed_notes: int
    stale_notes: int
    error_notes: int

    @classmethod
    def from_entity(cls, status: ObsidianVaultStatus) -> ObsidianStatusResponse:
        """Create schema from entity.

        Args:
            status: Domain status entity.

        Returns:
            HTTP response schema.
        """
        return cls(
            vault_path=status.vault_path,
            alexandria_root=status.alexandria_root,
            vault_exists=status.vault_exists,
            alexandria_root_exists=status.alexandria_root_exists,
            indexed_notes=status.indexed_notes,
            stale_notes=status.stale_notes,
            error_notes=status.error_notes,
        )


class ObsidianReindexResponse(StrictSchemaModel):
    """Vault reindex response."""

    files_seen: int
    files_indexed: int
    files_skipped: int
    stale_marked: int
    errors: list[str]

    @classmethod
    def from_entity(cls, result: ObsidianReindexResult) -> ObsidianReindexResponse:
        """Create schema from entity.

        Args:
            result: Domain reindex result.

        Returns:
            HTTP response schema.
        """
        return cls(
            files_seen=result.files_seen,
            files_indexed=result.files_indexed,
            files_skipped=result.files_skipped,
            stale_marked=result.stale_marked,
            errors=result.errors,
        )


class ObsidianNoteResponse(StrictSchemaModel):
    """One indexed Obsidian note response."""

    id: str
    alexandria_type: AlexandriaNoteType
    path: str
    title: str
    status: str
    tags: list[str]
    project: str | None
    source: str | None
    content_hash: str
    frontmatter: JSONObject
    body: str
    index_status: ObsidianIndexStatus
    error_message: str | None
    size_bytes: int
    modified_at: AwareTimestamp
    indexed_at: AwareTimestamp
    wikilink: str

    @classmethod
    def from_entity(cls, note: ObsidianNote) -> ObsidianNoteResponse:
        """Create schema from entity.

        Args:
            note: Domain note entity.

        Returns:
            HTTP response schema.
        """
        return cls(
            id=note.note_id,
            alexandria_type=note.alexandria_type,
            path=note.relative_path,
            title=note.title,
            status=note.status,
            tags=note.tags,
            project=note.project,
            source=note.source,
            content_hash=note.content_hash,
            frontmatter=note.frontmatter,
            body=note.body,
            index_status=note.index_status,
            error_message=note.error_message,
            size_bytes=note.size_bytes,
            modified_at=note.modified_at,
            indexed_at=note.indexed_at,
            wikilink=f"[[{note.relative_path.removesuffix('.md')}]]",
        )


class ObsidianSearchRequest(StrictSchemaModel):
    """Search request for Obsidian-backed Alexandria notes."""

    query: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=50)
    alexandria_type: AlexandriaNoteType | None = None
    project: str | None = None
    tags: list[str] = Field(default_factory=list)

    def to_query(self) -> ObsidianSearchQuery:
        """Convert to application search query.

        Returns:
            Application search query.
        """
        return ObsidianSearchQuery(
            query=self.query,
            limit=self.limit,
            alexandria_type=_optional_note_type(self.alexandria_type),
            project=self.project,
            tags=self.tags,
        )


class ObsidianSearchHitResponse(StrictSchemaModel):
    """One Obsidian search hit."""

    note: ObsidianNoteResponse
    excerpt: str
    score: float
    chunk_id: str | None
    heading_path: str | None

    @classmethod
    def from_entity(cls, hit: ObsidianSearchHit) -> ObsidianSearchHitResponse:
        """Create schema from search hit.

        Args:
            hit: Domain search hit.

        Returns:
            HTTP search hit schema.
        """
        return cls(
            note=ObsidianNoteResponse.from_entity(hit.note),
            excerpt=hit.excerpt,
            score=hit.score,
            chunk_id=hit.chunk_id,
            heading_path=hit.heading_path,
        )


class ObsidianSearchResponse(StrictSchemaModel):
    """Obsidian search response."""

    items: list[ObsidianSearchHitResponse]
    total: int


class ObsidianSaveNoteRequest(StrictSchemaModel):
    """Request to create one Alexandria-managed Obsidian note."""

    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    alexandria_type: AlexandriaNoteType
    id: str | None = None
    path: str | None = None
    tags: list[str] = Field(default_factory=list)
    status: str = "active"
    project: str | None = None
    source: str = "mcp"
    frontmatter: JSONObject = Field(default_factory=dict)

    def to_command(self) -> ObsidianSaveNote:
        """Convert request into application save command.

        Returns:
            Application save command.
        """
        return ObsidianSaveNote(
            title=self.title,
            body=self.body,
            alexandria_type=_note_type(self.alexandria_type),
            note_id=self.id,
            relative_path=self.path,
            tags=self.tags,
            status=self.status,
            project=self.project,
            source=self.source,
            frontmatter=self.frontmatter,
        )


class ObsidianLibrarianAskRequest(StrictSchemaModel):
    """Ask the Obsidian-aware Alexandria librarian."""

    query: str = Field(min_length=1)
    active_note_path: str | None = None
    selection: str | None = None
    project: str | None = None
    preferred_alexandria_types: list[AlexandriaNoteType] = Field(default_factory=list)
    save_transcript: bool = False
    delegate_to_librarian: bool = False

    def to_command(self) -> ObsidianLibrarianAsk:
        """Convert request into application command.

        Returns:
            Application librarian ask command.
        """
        return ObsidianLibrarianAsk(
            query=self.query,
            active_note_path=self.active_note_path,
            selection=self.selection,
            project=self.project,
            preferred_alexandria_types=[
                _note_type(note_type) for note_type in self.preferred_alexandria_types
            ],
            save_transcript=self.save_transcript,
            delegate_to_librarian=self.delegate_to_librarian,
        )


class ObsidianSourceRefResponse(StrictSchemaModel):
    """Source reference returned from an Obsidian librarian answer."""

    id: str
    alexandria_type: str
    path: str
    title: str
    wikilink: str


class ObsidianLibrarianAskResponse(StrictSchemaModel):
    """Response from the Obsidian-aware librarian adapter."""

    answer_markdown: str
    source_refs: list[ObsidianSourceRefResponse]
    action_preview: list[str]
    conversation_id: str
    transcript_path: str | None


def _note_type(value: AlexandriaNoteType | str) -> AlexandriaNoteType:
    if isinstance(value, AlexandriaNoteType):
        return value
    return AlexandriaNoteType(value)


def _optional_note_type(
    value: AlexandriaNoteType | str | None,
) -> AlexandriaNoteType | None:
    if value is None:
        return None
    return _note_type(value)
