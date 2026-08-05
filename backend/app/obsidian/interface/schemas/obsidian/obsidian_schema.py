"""HTTP schemas for Obsidian vault operations."""

from __future__ import annotations

from dataclasses import replace

from app.obsidian.application.notes.frontmatter_metadata_normalization import (
    normalize_known_frontmatter_metadata,
    normalize_string_collection,
)
from app.obsidian.application.service.obsidian_vault_reindex_service import (
    ObsidianVaultReindexReport,
)
from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianReportBundleOwner,
    ObsidianReportBundleRequest,
    ObsidianReportBundleVerify,
    ObsidianSaveNote,
    ObsidianSearchQuery,
    ObsidianWriteNote,
)
from app.obsidian.domain.entities.obsidian_note import (
    ObsidianCanonicalIdentityResult,
    ObsidianExactPathStatus,
    ObsidianIndexError,
    ObsidianNote,
    ObsidianNoteWriteResult,
    ObsidianReindexResult,
    ObsidianRelatedNote,
    ObsidianReportBundleResult,
    ObsidianSearchHit,
    ObsidianVaultStatus,
)
from app.obsidian.domain.event_enum.obsidian_enums import (
    AlexandriaNoteType,
    ObsidianEdgeSourceKind,
    ObsidianFrontmatterMode,
    ObsidianIndexErrorCode,
    ObsidianIndexStatus,
    ObsidianRelationType,
    ObsidianReportBundleCompletionStatus,
    ObsidianWriteMatchBy,
    ObsidianWriteMode,
    ObsidianWriteOperation,
)
from app.obsidian.interface.schemas.obsidian.obsidian_graph_projection_schema import (
    ObsidianGraphProjectionRebuildResponse,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.schemas.datetime_schemas import AwareTimestamp
from app.shared.types.extra_types import JSONObject, JSONValue
from pydantic import Field, field_validator


class ObsidianStatusResponse(StrictSchemaModel):
    """Current Obsidian vault/index status."""

    vault_path: str
    alexandria_root: str
    vault_exists: bool
    alexandria_root_exists: bool
    indexed_notes: int
    stale_notes: int
    error_notes: int
    index_errors: list[ObsidianIndexErrorResponse]

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
            index_errors=[
                ObsidianIndexErrorResponse.from_entity(error)
                for error in status.index_errors
            ],
        )


class ObsidianIndexErrorResponse(StrictSchemaModel):
    """Structured note-index failure returned to operators."""

    note_path: str
    context_id: str | None
    error_code: ObsidianIndexErrorCode
    error_message: str
    detected_at: AwareTimestamp

    @classmethod
    def from_entity(cls, error: ObsidianIndexError) -> ObsidianIndexErrorResponse:
        return cls(
            note_path=error.note_path,
            context_id=error.context_id,
            error_code=error.error_code,
            error_message=error.error_message,
            detected_at=error.detected_at,
        )


class ObsidianReindexResponse(StrictSchemaModel):
    """Vault reindex response."""

    files_seen: int
    files_indexed: int
    files_skipped: int
    stale_marked: int
    errors: list[str]
    error_details: list[ObsidianIndexErrorResponse]
    skip_reasons: dict[str, int] = Field(default_factory=dict)
    edge_targets_resolved: int = 0
    graph_projection: ObsidianGraphProjectionRebuildResponse | None = None

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
            error_details=[
                ObsidianIndexErrorResponse.from_entity(error)
                for error in result.error_details
            ],
            skip_reasons=result.skip_reasons,
            edge_targets_resolved=result.edge_targets_resolved,
        )

    @classmethod
    def from_reindex_report(
        cls,
        report: ObsidianVaultReindexReport,
    ) -> ObsidianReindexResponse:
        """Create schema from a public composite reindex report.

        Args:
            report: Combined SQLite and optional graph projection report.

        Returns:
            HTTP response schema with fresh graph projection evidence.
        """
        result = report.vault_index
        return cls(
            files_seen=result.files_seen,
            files_indexed=result.files_indexed,
            files_skipped=result.files_skipped,
            stale_marked=result.stale_marked,
            errors=result.errors,
            error_details=[
                ObsidianIndexErrorResponse.from_entity(error)
                for error in result.error_details
            ],
            skip_reasons=result.skip_reasons,
            edge_targets_resolved=result.edge_targets_resolved,
            graph_projection=ObsidianGraphProjectionRebuildResponse.from_entity(
                report.graph_projection
            ),
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


class ObsidianExactPathStatusResponse(StrictSchemaModel):
    """Exact managed-path existence response."""

    exists: bool
    note_id: str | None
    path: str
    index_status: ObsidianIndexStatus | None

    @classmethod
    def from_entity(
        cls,
        result: ObsidianExactPathStatus,
    ) -> ObsidianExactPathStatusResponse:
        """Create an exact-path response.

        Args:
            result: Value supplied to from_entity.

        Returns:
            Result produced by from_entity.
        """
        return cls(
            exists=result.exists,
            note_id=result.note_id,
            path=result.relative_path,
            index_status=result.index_status,
        )


class ObsidianCanonicalIdentityRequest(StrictSchemaModel):
    """Logical report identity used for alias-aware resolution."""

    project: str = Field(min_length=1)
    report: str = Field(min_length=1)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    entity: str = Field(min_length=1)
    edition: str | None = None


class ObsidianCanonicalIdentityResponse(StrictSchemaModel):
    """Canonical report family/path resolution response."""

    canonical_report_family: str
    canonical_entity: str
    canonical_path: str
    existing_note_id: str | None
    aliases: list[str]
    resolution: str
    candidate_paths: list[str]

    @classmethod
    def from_entity(
        cls,
        result: ObsidianCanonicalIdentityResult,
    ) -> ObsidianCanonicalIdentityResponse:
        """Create a canonical identity response.

        Args:
            result: Value supplied to from_entity.

        Returns:
            Result produced by from_entity.
        """
        return cls(
            canonical_report_family=result.canonical_report_family,
            canonical_entity=result.canonical_entity,
            canonical_path=result.canonical_path,
            existing_note_id=result.existing_note_id,
            aliases=result.aliases,
            resolution=result.resolution,
            candidate_paths=result.candidate_paths,
        )


class ObsidianSearchRequest(StrictSchemaModel):
    """Search request for Obsidian-backed Alexandria notes."""

    query: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=50)
    alexandria_type: AlexandriaNoteType | None = None
    project: str | None = None
    tags: list[str] = Field(default_factory=list)
    refresh: bool = False

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: JSONValue) -> list[str]:
        """Normalize tag filters without accepting nested or numeric values.

        Args:
            value: Raw tag filter input.

        Returns:
            Canonical ordered tag filters.
        """
        return normalize_string_collection(value)

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
            tags=tuple(self.tags),
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


class ObsidianRelatedNoteResponse(StrictSchemaModel):
    """One graph-related Obsidian note."""

    note: ObsidianNoteResponse
    relation: ObsidianRelationType
    source_kind: ObsidianEdgeSourceKind
    direction: str
    score: float
    edge_id: str

    @classmethod
    def from_entity(cls, item: ObsidianRelatedNote) -> ObsidianRelatedNoteResponse:
        """Create schema from related-note entity.

        Args:
            item: Related-note entity.

        Returns:
            HTTP related-note schema.
        """
        return cls(
            note=ObsidianNoteResponse.from_entity(item.note),
            relation=item.relation,
            source_kind=item.source_kind,
            direction=item.direction,
            score=item.score,
            edge_id=item.edge_id,
        )


class ObsidianRelatedNotesResponse(StrictSchemaModel):
    """Related notes response."""

    items: list[ObsidianRelatedNoteResponse]
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
    expected_content_hash: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: JSONValue) -> list[str]:
        """Normalize note tags at the external HTTP boundary.

        Args:
            value: Raw note tag input.

        Returns:
            Canonical ordered note tags.
        """
        return normalize_string_collection(value)

    @field_validator("frontmatter", mode="before")
    @classmethod
    def normalize_frontmatter(cls, value: JSONObject) -> JSONObject:
        """Normalize known typed metadata before building the internal command.

        Args:
            value: Raw JSON-compatible frontmatter payload.

        Returns:
            Copied frontmatter with canonical collection and Boolean values.
        """
        normalized = dict(value)
        normalize_known_frontmatter_metadata(normalized)
        return normalized

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
            tags=tuple(self.tags),
            status=self.status,
            project=self.project,
            source=self.source,
            frontmatter=self.frontmatter,
            expected_content_hash=self.expected_content_hash,
        )


class ObsidianWriteNoteRequest(ObsidianSaveNoteRequest):
    """Explicit note write request with exact identity and merge semantics."""

    match_by: ObsidianWriteMatchBy
    frontmatter_mode: ObsidianFrontmatterMode = ObsidianFrontmatterMode.MERGE

    def to_write_command(self, write_mode: ObsidianWriteMode) -> ObsidianWriteNote:
        """Convert the external request to an explicit application command.

        Args:
            write_mode: Value supplied to to_write_command.

        Returns:
            Result produced by to_write_command.
        """
        return ObsidianWriteNote(
            note=self.to_command(),
            write_mode=write_mode,
            match_by=ObsidianWriteMatchBy(self.match_by),
            frontmatter_mode=ObsidianFrontmatterMode(self.frontmatter_mode),
            provided_fields=frozenset(self.model_fields_set),
        )


class ObsidianWritePipelineResponse(StrictSchemaModel):
    """Observed stages completed by one explicit canonical note write."""

    storage_status: str
    metadata_status: str
    fts_status: str
    sqlite_graph_edge_status: str
    graph_projection_status: str


class ObsidianNoteWriteResponse(StrictSchemaModel):
    """Explicit write outcome without overloading note index status."""

    operation: ObsidianWriteOperation
    write_mode: ObsidianWriteMode
    match_by: ObsidianWriteMatchBy
    note: ObsidianNoteResponse
    pipeline: ObsidianWritePipelineResponse
    reindex_required: bool
    warnings: list[str]

    @classmethod
    def from_entity(
        cls,
        result: ObsidianNoteWriteResult,
    ) -> ObsidianNoteWriteResponse:
        """Create a response from the domain write outcome.

        Args:
            result: Value supplied to from_entity.

        Returns:
            Result produced by from_entity.
        """
        return cls(
            operation=result.operation,
            write_mode=result.write_mode,
            match_by=result.match_by,
            note=ObsidianNoteResponse.from_entity(result.note),
            pipeline=ObsidianWritePipelineResponse(
                storage_status=result.storage_status,
                metadata_status=result.metadata_status,
                fts_status=result.fts_status,
                sqlite_graph_edge_status=result.sqlite_graph_edge_status,
                graph_projection_status=result.graph_projection_status,
            ),
            reindex_required=result.reindex_required,
            warnings=result.warnings,
        )


class ObsidianReportBundleSourceRequest(ObsidianSaveNoteRequest):
    """Canonical source payload for one report bundle."""

    alexandria_type: AlexandriaNoteType = AlexandriaNoteType.CONTEXT

    def to_command(self) -> ObsidianSaveNote:
        """Apply generic Context defaults while preserving explicit metadata.

        Returns:
            Result produced by to_command.
        """
        command = super().to_command()
        frontmatter = dict(command.frontmatter)
        project_value = command.project or frontmatter.get("project")
        project = project_value if isinstance(project_value, str) else None
        if command.alexandria_type is AlexandriaNoteType.CONTEXT:
            frontmatter.setdefault("scope", "PROJECT" if project else "GLOBAL")
        return replace(command, project=project, frontmatter=frontmatter)


class ObsidianReportBundleOwnerRequest(StrictSchemaModel):
    """Existing graph owner to link to the report source."""

    path: str = Field(min_length=1)
    relation: ObsidianRelationType = ObsidianRelationType.CONTAINS

    def to_command(self) -> ObsidianReportBundleOwner:
        """Convert to an immutable owner contract.

        Returns:
            Result produced by to_command.
        """
        return ObsidianReportBundleOwner(
            path=self.path,
            relation=ObsidianRelationType(self.relation),
        )


class ObsidianReportBundleVerifyRequest(StrictSchemaModel):
    """Requested post-write verification stages."""

    index_status: bool = True
    incoming_edges: bool = True
    duplicates: bool = True

    def to_command(self) -> ObsidianReportBundleVerify:
        """Convert to an immutable verification contract.

        Returns:
            Result produced by to_command.
        """
        return ObsidianReportBundleVerify(
            index_status=self.index_status,
            incoming_edges=self.incoming_edges,
            duplicates=self.duplicates,
        )


class ObsidianReportBundleRequestSchema(StrictSchemaModel):
    """Idempotent Source/Index/Hub operation request."""

    idempotency_key: str = Field(min_length=1, max_length=512)
    source: ObsidianReportBundleSourceRequest
    graph_owners: list[ObsidianReportBundleOwnerRequest] = Field(default_factory=list)
    reindex: bool = True
    verify: ObsidianReportBundleVerifyRequest = Field(
        default_factory=ObsidianReportBundleVerifyRequest
    )

    def to_command(self) -> ObsidianReportBundleRequest:
        """Convert to the application report bundle command.

        Returns:
            Result produced by to_command.
        """
        return ObsidianReportBundleRequest(
            idempotency_key=self.idempotency_key,
            source=self.source.to_command(),
            graph_owners=tuple(owner.to_command() for owner in self.graph_owners),
            reindex=self.reindex,
            verify=self.verify.to_command(),
        )


class ObsidianReportBundleSourceResponse(StrictSchemaModel):
    """Source write result included in a report bundle response."""

    note_id: str
    path: str
    operation: ObsidianWriteOperation
    index_status: ObsidianIndexStatus


class ObsidianReportBundleGraphResponse(StrictSchemaModel):
    """Expected and verified incoming graph edges."""

    expected_incoming_edges: int
    verified_incoming_edges: int
    unresolved_links: list[str]


class ObsidianReportBundleResponse(StrictSchemaModel):
    """Checkpointable report bundle completion response."""

    completion_status: ObsidianReportBundleCompletionStatus
    idempotency_key: str
    replayed: bool
    source: ObsidianReportBundleSourceResponse | None
    owner_operations: list[ObsidianWriteOperation]
    graph: ObsidianReportBundleGraphResponse
    duplicates: list[str]
    failed_stage: str | None
    rollback_performed: bool
    errors: list[JSONObject]

    @classmethod
    def from_entity(
        cls,
        result: ObsidianReportBundleResult,
    ) -> ObsidianReportBundleResponse:
        """Create a public response from a report bundle outcome.

        Args:
            result: Value supplied to from_entity.

        Returns:
            Result produced by from_entity.
        """
        source = None
        if result.source is not None:
            source = ObsidianReportBundleSourceResponse(
                note_id=result.source.note.note_id,
                path=result.source.note.relative_path,
                operation=result.source.operation,
                index_status=result.source.note.index_status,
            )
        return cls(
            completion_status=result.completion_status,
            idempotency_key=result.idempotency_key,
            replayed=result.replayed,
            source=source,
            owner_operations=[item.operation for item in result.owner_writes],
            graph=ObsidianReportBundleGraphResponse(
                expected_incoming_edges=result.graph.expected_incoming_edges,
                verified_incoming_edges=result.graph.verified_incoming_edges,
                unresolved_links=result.graph.unresolved_links,
            ),
            duplicates=result.duplicates,
            failed_stage=result.failed_stage,
            rollback_performed=result.rollback_performed,
            errors=result.errors,
        )


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
