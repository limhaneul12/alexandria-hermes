"""Per-note diagnostics for indexed Obsidian graph links."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Literal, cast

from app.obsidian.application.graph.obsidian_graph_projection_rebuild_service import (
    ObsidianGraphProjectionRebuildReport,
    ObsidianGraphProjectionRebuildService,
    ObsidianGraphProjectionStatusReport,
)
from app.obsidian.application.notes.obsidian_note_indexer import note_index_from_path
from app.obsidian.domain.entities.obsidian_note import ObsidianEdge, ObsidianNote
from app.obsidian.domain.event_enum.obsidian_enums import ObsidianIndexStatus
from app.obsidian.domain.repositories.obsidian_graph_projection_source_repository import (
    IObsidianGraphProjectionSourceRepository,
)
from app.obsidian.domain.repositories.obsidian_index_query_repository import (
    IObsidianIndexQueryRepository,
)
from app.obsidian.domain.repositories.obsidian_repository import (
    IObsidianIndexRepository,
)
from app.obsidian.infrastructure.markdown.paths import (
    resolve_note_path,
    safe_relative_path,
)
from app.obsidian.infrastructure.obsidian_vault_config_store import (
    ObsidianVaultConfigStore,
)
from app.shared.application.index_maintenance_coordinator import (
    IndexMaintenanceCoordinator,
)
from app.shared.exceptions.obsidian_exceptions import (
    ObsidianNotFoundError,
    ObsidianValidationError,
)

GraphLinkValidationIssueCode = Literal[
    "missing_target_note",
    "ambiguous_target_note",
    "target_not_indexed",
]


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianGraphNoteSelector:
    """Exact note selector supplied at the diagnostics boundary."""

    note_id: str | None = None
    path: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianGraphNoteIndexDiagnostic:
    """Indexed-note existence and health for one diagnostics request."""

    exists: bool
    note_id: str | None = None
    relative_path: str | None = None
    title: str | None = None
    index_status: str | None = None
    error_message: str | None = None
    projection_included: bool = False


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianGraphResolvedTargetDiagnostic:
    """One outgoing edge that resolves to a healthy indexed note."""

    edge_id: str
    target_note_id: str
    target_path: str
    relation: str
    source_kind: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianGraphUnresolvedTargetDiagnostic:
    """One outgoing edge target that cannot be projected as a stable note edge."""

    edge_id: str
    target_path: str
    relation: str
    source_kind: str
    code: GraphLinkValidationIssueCode
    detail: str
    target_note_id: str | None = None
    candidate_note_ids: tuple[str, ...] = field(default_factory=tuple)
    candidate_paths: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Normalize candidate collections to immutable tuples."""
        object.__setattr__(self, "candidate_note_ids", tuple(self.candidate_note_ids))
        object.__setattr__(self, "candidate_paths", tuple(self.candidate_paths))


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianGraphOutgoingLinkDiagnostic:
    """Counts and bounded details for outgoing graph edges from one note."""

    parsed_count: int
    resolved_count: int
    unresolved_count: int
    unresolved_targets: tuple[ObsidianGraphUnresolvedTargetDiagnostic, ...] = field(
        default_factory=tuple
    )
    resolved_targets: tuple[ObsidianGraphResolvedTargetDiagnostic, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        """Normalize edge detail collections to immutable tuples."""
        object.__setattr__(self, "unresolved_targets", tuple(self.unresolved_targets))
        object.__setattr__(self, "resolved_targets", tuple(self.resolved_targets))


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianGraphNoteLinkValidationReport:
    """Stable per-note link validation report for REST and MCP boundaries."""

    selector: ObsidianGraphNoteSelector
    note: ObsidianGraphNoteIndexDiagnostic
    outgoing: ObsidianGraphOutgoingLinkDiagnostic
    projection_status: ObsidianGraphProjectionStatusReport


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianGraphNoteRebuildReport:
    """Focused indexed-edge refresh followed by snapshot projection activation."""

    replace_existing_edges: bool
    validation: ObsidianGraphNoteLinkValidationReport
    projection: ObsidianGraphProjectionRebuildReport


class ObsidianGraphNoteDiagnosticsService:
    """Validate one note's cached outgoing graph links without mutation."""

    def __init__(
        self,
        *,
        repository: IObsidianIndexQueryRepository,
        source: IObsidianGraphProjectionSourceRepository,
        projection_service: ObsidianGraphProjectionRebuildService,
        vault_config_store: ObsidianVaultConfigStore | None = None,
        index_maintenance_coordinator: IndexMaintenanceCoordinator | None = None,
    ) -> None:
        """Create per-note graph diagnostics service.

        Args:
            repository: Indexed-note query repository.
            source: Read-only graph projection source rows.
            projection_service: Existing graph projection status provider.
        """
        self._repository = repository
        self._source = source
        self._projection_service = projection_service
        self._vault_config_store = vault_config_store
        self._index_maintenance_coordinator = index_maintenance_coordinator

    async def build_status(self) -> ObsidianGraphProjectionStatusReport:
        """Return the current snapshot projection status without rebuilding.

        Returns:
            Existing optional graph projection status report.
        """
        return await self._projection_service.status()

    async def validate_note_links(
        self,
        *,
        note_id: str | None = None,
        path: str | None = None,
        include_resolved_targets: bool = False,
    ) -> ObsidianGraphNoteLinkValidationReport:
        """Validate cached outgoing graph links for one exact note selector.

        Args:
            note_id: Stable note id selector.
            path: Vault-relative exact path selector.
            include_resolved_targets: Include resolved edge details in addition to
                always-exposed unresolved details.

        Returns:
            Per-note graph diagnostics plus existing projection status.
        """
        selector = _selector(note_id=note_id, path=path)
        note = await self._selected_note(selector)
        projection_status = await self.build_status()
        if note is None:
            return ObsidianGraphNoteLinkValidationReport(
                selector=selector,
                note=ObsidianGraphNoteIndexDiagnostic(exists=False),
                outgoing=ObsidianGraphOutgoingLinkDiagnostic(
                    parsed_count=0,
                    resolved_count=0,
                    unresolved_count=0,
                ),
                projection_status=projection_status,
            )
        notes = await self._source.list_projection_notes()
        edges = tuple(
            edge
            for edge in await self._source.list_projection_edges()
            if edge.source_note_id == note.note_id
        )
        outgoing = _outgoing_diagnostics(
            edges,
            notes=notes,
            include_resolved_targets=include_resolved_targets,
        )
        return ObsidianGraphNoteLinkValidationReport(
            selector=selector,
            note=ObsidianGraphNoteIndexDiagnostic(
                exists=True,
                note_id=note.note_id,
                relative_path=note.relative_path,
                title=note.title,
                index_status=note.index_status.value,
                error_message=note.error_message,
                projection_included=note.index_status is ObsidianIndexStatus.INDEXED,
            ),
            outgoing=outgoing,
            projection_status=projection_status,
        )

    async def rebuild_note_graph(
        self,
        *,
        note_id: str | None = None,
        path: str | None = None,
        replace_existing_edges: bool = True,
    ) -> ObsidianGraphNoteRebuildReport:
        """Reparse one canonical note's edges, then activate a full projection.

        Args:
            note_id: Value supplied to rebuild_note_graph.
            path: Value supplied to rebuild_note_graph.
            replace_existing_edges: Value supplied to rebuild_note_graph.

        Returns:
            Result produced by rebuild_note_graph.
        """
        if not replace_existing_edges:
            raise ObsidianValidationError(
                "replace_existing_edges=false is unsupported for canonical edge rebuilds"
            )
        if (
            self._vault_config_store is None
            or self._index_maintenance_coordinator is None
        ):
            raise ObsidianValidationError("note graph rebuild is not configured")
        selector = _selector(note_id=note_id, path=path)
        note = await self._selected_note(selector)
        if note is None:
            raise ObsidianNotFoundError("Obsidian note graph target was not found")
        config = self._vault_config_store.current()
        absolute = resolve_note_path(config.vault_path, note.relative_path)
        payload = note_index_from_path(
            absolute,
            note.relative_path,
            alexandria_root=config.alexandria_root,
        )
        if payload is None:
            raise ObsidianValidationError(
                "Obsidian note is missing Alexandria frontmatter"
            )
        write_repository = cast(IObsidianIndexRepository, self._repository)
        async with self._index_maintenance_coordinator.operation("note_graph_rebuild"):
            await write_repository.upsert_note(payload)
            await write_repository.resolve_edge_targets()
        projection = await self._projection_service.rebuild(
            include_issue_details=True,
        )
        validation = await self.validate_note_links(
            note_id=note.note_id,
            include_resolved_targets=True,
        )
        return ObsidianGraphNoteRebuildReport(
            replace_existing_edges=True,
            validation=validation,
            projection=projection,
        )

    async def _selected_note(
        self,
        selector: ObsidianGraphNoteSelector,
    ) -> ObsidianNote | None:
        note_by_id = (
            await self._repository.get_by_id(selector.note_id)
            if selector.note_id is not None
            else None
        )
        note_by_path = (
            await self._repository.get_by_path(selector.path)
            if selector.path is not None
            else None
        )
        if note_by_id is not None and note_by_path is not None:
            if note_by_id.note_id != note_by_path.note_id:
                raise ObsidianValidationError(
                    "note_id and path selectors refer to different Obsidian notes"
                )
            return note_by_id
        return note_by_id or note_by_path


def _selector(
    *,
    note_id: str | None,
    path: str | None,
) -> ObsidianGraphNoteSelector:
    normalized_note_id = _normalize_note_id(note_id)
    normalized_path = _normalize_path(path)
    if normalized_note_id is None and normalized_path is None:
        raise ObsidianValidationError("note_id or path is required")
    return ObsidianGraphNoteSelector(
        note_id=normalized_note_id,
        path=normalized_path,
    )


def _normalize_note_id(note_id: str | None) -> str | None:
    if note_id is None:
        return None
    normalized = note_id.strip()
    if not normalized:
        raise ObsidianValidationError("note_id must not be blank")
    return normalized


def _normalize_path(path: str | None) -> str | None:
    if path is None:
        return None
    normalized = str(safe_relative_path(path.strip()))
    if not normalized:
        raise ObsidianValidationError("path must not be blank")
    return normalized


def _outgoing_diagnostics(
    edges: tuple[ObsidianEdge, ...],
    *,
    notes: tuple[ObsidianNote, ...],
    include_resolved_targets: bool,
) -> ObsidianGraphOutgoingLinkDiagnostic:
    notes_by_id = {note.note_id: note for note in notes}
    notes_by_path = {note.relative_path: note for note in notes}
    healthy_notes = tuple(
        note for note in notes if note.index_status is ObsidianIndexStatus.INDEXED
    )
    healthy_notes_by_id = {note.note_id: note for note in healthy_notes}
    healthy_notes_by_path = {note.relative_path: note for note in healthy_notes}
    healthy_notes_by_link_name = _notes_by_link_name(healthy_notes)
    resolved: list[ObsidianGraphResolvedTargetDiagnostic] = []
    unresolved: list[ObsidianGraphUnresolvedTargetDiagnostic] = []
    for edge in sorted(edges, key=lambda item: item.edge_id):
        target = _resolve_target(
            edge,
            notes_by_id=notes_by_id,
            notes_by_path=notes_by_path,
            healthy_notes_by_id=healthy_notes_by_id,
            healthy_notes_by_path=healthy_notes_by_path,
            healthy_notes_by_link_name=healthy_notes_by_link_name,
        )
        if isinstance(target, ObsidianGraphResolvedTargetDiagnostic):
            resolved.append(target)
        else:
            unresolved.append(target)
    return ObsidianGraphOutgoingLinkDiagnostic(
        parsed_count=len(edges),
        resolved_count=len(resolved),
        unresolved_count=len(unresolved),
        unresolved_targets=tuple(unresolved),
        resolved_targets=tuple(resolved) if include_resolved_targets else (),
    )


def _resolve_target(
    edge: ObsidianEdge,
    *,
    notes_by_id: dict[str, ObsidianNote],
    notes_by_path: dict[str, ObsidianNote],
    healthy_notes_by_id: dict[str, ObsidianNote],
    healthy_notes_by_path: dict[str, ObsidianNote],
    healthy_notes_by_link_name: dict[str, tuple[ObsidianNote, ...]],
) -> ObsidianGraphResolvedTargetDiagnostic | ObsidianGraphUnresolvedTargetDiagnostic:
    if edge.target_note_id is not None:
        target = healthy_notes_by_id.get(edge.target_note_id)
        if target is not None:
            return _resolved_target(edge, target)
        unhealthy = notes_by_id.get(edge.target_note_id)
        if unhealthy is not None:
            return _unresolved_target_not_indexed(edge, unhealthy)
        path_candidate = healthy_notes_by_path.get(edge.target_path)
        return ObsidianGraphUnresolvedTargetDiagnostic(
            edge_id=edge.edge_id,
            target_note_id=edge.target_note_id,
            target_path=edge.target_path,
            relation=edge.relation.value,
            source_kind=edge.source_kind.value,
            code="missing_target_note",
            detail="explicit edge target id is absent from the Obsidian index",
            candidate_note_ids=(
                () if path_candidate is None else (path_candidate.note_id,)
            ),
            candidate_paths=(
                () if path_candidate is None else (path_candidate.relative_path,)
            ),
        )
    target = healthy_notes_by_path.get(edge.target_path)
    if target is not None:
        return _resolved_target(edge, target)
    unhealthy = notes_by_path.get(edge.target_path)
    if unhealthy is not None:
        return _unresolved_target_not_indexed(edge, unhealthy)
    candidates = healthy_notes_by_link_name.get(_link_name(edge.target_path), ())
    if len(candidates) == 1:
        return _resolved_target(edge, candidates[0])
    if len(candidates) > 1:
        return ObsidianGraphUnresolvedTargetDiagnostic(
            edge_id=edge.edge_id,
            target_note_id=edge.target_note_id,
            target_path=edge.target_path,
            relation=edge.relation.value,
            source_kind=edge.source_kind.value,
            code="ambiguous_target_note",
            detail="edge target matches multiple healthy Obsidian notes",
            candidate_note_ids=tuple(note.note_id for note in candidates),
            candidate_paths=tuple(note.relative_path for note in candidates),
        )
    return ObsidianGraphUnresolvedTargetDiagnostic(
        edge_id=edge.edge_id,
        target_note_id=edge.target_note_id,
        target_path=edge.target_path,
        relation=edge.relation.value,
        source_kind=edge.source_kind.value,
        code="missing_target_note",
        detail="edge target is absent from the healthy Obsidian index",
    )


def _resolved_target(
    edge: ObsidianEdge,
    target: ObsidianNote,
) -> ObsidianGraphResolvedTargetDiagnostic:
    return ObsidianGraphResolvedTargetDiagnostic(
        edge_id=edge.edge_id,
        target_note_id=target.note_id,
        target_path=target.relative_path,
        relation=edge.relation.value,
        source_kind=edge.source_kind.value,
    )


def _unresolved_target_not_indexed(
    edge: ObsidianEdge,
    target: ObsidianNote,
) -> ObsidianGraphUnresolvedTargetDiagnostic:
    return ObsidianGraphUnresolvedTargetDiagnostic(
        edge_id=edge.edge_id,
        target_note_id=target.note_id,
        target_path=edge.target_path,
        relation=edge.relation.value,
        source_kind=edge.source_kind.value,
        code="target_not_indexed",
        detail=f"edge target exists with index_status={target.index_status.value}",
        candidate_note_ids=(target.note_id,),
        candidate_paths=(target.relative_path,),
    )


def _notes_by_link_name(
    notes: tuple[ObsidianNote, ...],
) -> dict[str, tuple[ObsidianNote, ...]]:
    grouped: defaultdict[str, list[ObsidianNote]] = defaultdict(list)
    for note in notes:
        names = {_link_name(note.relative_path), note.title.strip().casefold()}
        aliases = note.frontmatter.get("aliases")
        if isinstance(aliases, str):
            names.add(aliases.strip().casefold())
        elif isinstance(aliases, list):
            names.update(
                alias.strip().casefold()
                for alias in aliases
                if isinstance(alias, str) and alias.strip()
            )
        for name in names:
            if name:
                grouped[name].append(note)
    return {
        name: tuple(sorted(values, key=lambda item: item.relative_path))
        for name, values in grouped.items()
    }


def _link_name(path: str) -> str:
    return PurePosixPath(path).stem.strip().casefold()
