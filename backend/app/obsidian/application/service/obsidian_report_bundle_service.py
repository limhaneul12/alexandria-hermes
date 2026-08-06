"""Idempotent Source/owner/reindex/graph report bundle orchestration."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

from app.obsidian.application.graph.obsidian_graph_service import ObsidianGraphService
from app.obsidian.application.notes.obsidian_canonical_note_path import (
    canonical_managed_note_path,
)
from app.obsidian.application.service.obsidian_service import ObsidianService
from app.obsidian.application.service.obsidian_vault_reindex_service import (
    ObsidianVaultReindexService,
)
from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianReportBundleOwner,
    ObsidianReportBundleRequest,
    ObsidianSaveNote,
    ObsidianVaultInventoryRequest,
    ObsidianWriteNote,
)
from app.obsidian.domain.entities.obsidian_note import (
    ObsidianNote,
    ObsidianNoteWriteResult,
    ObsidianReportBundleGraphResult,
    ObsidianReportBundleResult,
)
from app.obsidian.domain.event_enum.obsidian_enums import (
    ObsidianFrontmatterMode,
    ObsidianIndexStatus,
    ObsidianRelationType,
    ObsidianReportBundleCompletionStatus,
    ObsidianWriteMatchBy,
    ObsidianWriteMode,
    ObsidianWriteOperation,
)
from app.obsidian.infrastructure.obsidian_report_bundle_run_store import (
    ObsidianReportBundleRunStore,
)
from app.obsidian.infrastructure.obsidian_vault_config_store import (
    ObsidianVaultConfigStore,
)
from app.shared.application.index_maintenance_coordinator import (
    IndexMaintenanceCoordinator,
)
from app.shared.exceptions.common_exceptions import IndexMaintenanceConflictError
from app.shared.exceptions.obsidian_exceptions import (
    ObsidianDomainError,
    ObsidianIdempotencyConflictError,
    ObsidianNotFoundError,
    ObsidianValidationError,
)
from app.shared.types.extra_types import JSONObject, JSONValue


class ObsidianReportBundleService:
    """Own one durable, retry-safe report write and graph verification boundary."""

    def __init__(
        self,
        *,
        obsidian_service: ObsidianService,
        vault_reindex_service: ObsidianVaultReindexService,
        graph_service: ObsidianGraphService,
        vault_config_store: ObsidianVaultConfigStore,
        index_maintenance_coordinator: IndexMaintenanceCoordinator,
    ) -> None:
        self._obsidian_service = obsidian_service
        self._vault_reindex_service = vault_reindex_service
        self._graph_service = graph_service
        self._vault_config_store = vault_config_store
        self._index_maintenance_coordinator = index_maintenance_coordinator

    async def upsert(
        self,
        request: ObsidianReportBundleRequest,
    ) -> ObsidianReportBundleResult:
        """Upsert a report source, update owners, rebuild, and verify graph edges.

        Args:
            request: Value supplied to upsert.

        Returns:
            Result produced by upsert.
        """
        async with self._index_maintenance_coordinator.write_operation(
            "obsidian_report_bundle"
        ):
            return await self._upsert_serialized(request)

    async def _upsert_serialized(
        self,
        request: ObsidianReportBundleRequest,
    ) -> ObsidianReportBundleResult:
        key = request.idempotency_key.strip()
        if not key:
            raise ObsidianValidationError("idempotency_key is required")
        normalized = self._normalized_request(replace(request, idempotency_key=key))
        request_hash = _request_hash(normalized)
        store = ObsidianReportBundleRunStore(
            vault_path=self._vault_config_store.current().vault_path
        )
        checkpoint = store.load(key)
        if checkpoint is not None and checkpoint.get("request_hash") != request_hash:
            raise ObsidianIdempotencyConflictError
        replay = await self._completed_replay(normalized, checkpoint)
        if replay is not None:
            return replay

        try:
            owners = [
                await self._obsidian_service.read_note_by_path(owner.path)
                for owner in normalized.graph_owners
            ]
        except ObsidianNotFoundError as exc:
            result = self._failure(
                request=normalized,
                status=ObsidianReportBundleCompletionStatus.FAILED_NO_MUTATION,
                stage="PREFLIGHT_GRAPH_OWNERS",
                error=exc,
            )
            self._save_checkpoint(store, normalized, request_hash, result)
            return result

        try:
            source_result = await self._obsidian_service.write_note(
                ObsidianWriteNote(
                    note=normalized.source,
                    write_mode=ObsidianWriteMode.UPSERT,
                    match_by=ObsidianWriteMatchBy.PATH,
                    frontmatter_mode=ObsidianFrontmatterMode.MERGE,
                )
            )
        except (OSError, ObsidianDomainError) as exc:
            result = self._failure(
                request=normalized,
                status=ObsidianReportBundleCompletionStatus.FAILED_NO_MUTATION,
                stage="UPSERT_SOURCE",
                error=exc,
            )
            self._save_checkpoint(store, normalized, request_hash, result)
            return result

        owner_writes: list[ObsidianNoteWriteResult] = []
        try:
            for owner_contract, owner_note in zip(
                normalized.graph_owners,
                owners,
                strict=True,
            ):
                owner_writes.append(
                    await self._update_owner(owner_contract, owner_note, source_result)
                )
        except (OSError, ObsidianDomainError) as exc:
            status = (
                ObsidianReportBundleCompletionStatus.PARTIAL_OWNER_UPDATE
                if owner_writes
                else ObsidianReportBundleCompletionStatus.PARTIAL_SOURCE_SAVED
            )
            result = self._failure(
                request=normalized,
                status=status,
                stage="UPDATE_GRAPH_OWNERS",
                error=exc,
                source=source_result,
                owner_writes=tuple(owner_writes),
            )
            self._save_checkpoint(store, normalized, request_hash, result)
            return result

        if not normalized.reindex:
            result = self._failure(
                request=normalized,
                status=ObsidianReportBundleCompletionStatus.PARTIAL_INDEXED,
                stage="REINDEX_DISABLED",
                error=ObsidianValidationError(
                    "report bundle verification requires reindex=true"
                ),
                source=source_result,
                owner_writes=tuple(owner_writes),
            )
            self._save_checkpoint(store, normalized, request_hash, result)
            return result

        try:
            reindex_report = await self._vault_reindex_service.rebuild()
            source_note = await self._obsidian_service.read_note(
                source_result.note.note_id
            )
        except (
            OSError,
            ObsidianDomainError,
            IndexMaintenanceConflictError,
        ) as exc:
            result = self._failure(
                request=normalized,
                status=ObsidianReportBundleCompletionStatus.PARTIAL_INDEXED,
                stage="REINDEX",
                error=exc,
                source=source_result,
                owner_writes=tuple(owner_writes),
            )
            self._save_checkpoint(store, normalized, request_hash, result)
            return result

        projection_status = reindex_report.graph_projection.status
        if projection_status == "failed" or (
            projection_status == "disabled" and normalized.verify.incoming_edges
        ):
            projection_error_items: list[JSONObject] = [
                {
                    "function": "graph_projection_rebuild",
                    "message": error.detail or error.code,
                    "code": error.code,
                }
                for error in reindex_report.graph_projection.errors
            ]
            if not projection_error_items:
                projection_error_items.append(
                    {
                        "function": "graph_projection_rebuild",
                        "message": f"graph projection rebuild was {projection_status}",
                    }
                )
            result = ObsidianReportBundleResult(
                completion_status=(
                    ObsidianReportBundleCompletionStatus.PARTIAL_GRAPH_UNVERIFIED
                ),
                idempotency_key=key,
                replayed=False,
                source=replace(source_result, note=source_note),
                owner_writes=tuple(owner_writes),
                graph=ObsidianReportBundleGraphResult(
                    expected_incoming_edges=len(normalized.graph_owners),
                    verified_incoming_edges=0,
                    unresolved_links=tuple(sorted(note.note_id for note in owners)),
                ),
                failed_stage="REBUILD_GRAPH_PROJECTION",
                errors=tuple(projection_error_items),
            )
            self._save_checkpoint(store, normalized, request_hash, result)
            return result

        if (
            normalized.verify.index_status
            and source_note.index_status is not ObsidianIndexStatus.INDEXED
        ):
            result = self._failure(
                request=normalized,
                status=ObsidianReportBundleCompletionStatus.PARTIAL_INDEXED,
                stage="VERIFY_INDEX_STATUS",
                error=ObsidianValidationError("source note is not indexed"),
                source=replace(source_result, note=source_note),
                owner_writes=tuple(owner_writes),
            )
            self._save_checkpoint(store, normalized, request_hash, result)
            return result

        source_result = replace(source_result, note=source_note)
        duplicates = (
            await self._duplicate_paths(normalized, source_note)
            if normalized.verify.duplicates
            else ()
        )
        expected_owner_ids = {note.note_id for note in owners}
        verified_owner_ids: set[str] = set()
        graph_errors: list[JSONObject] = []
        if normalized.verify.incoming_edges:
            try:
                related = await self._graph_service.related_notes(
                    source_note.note_id,
                    limit=max(10, len(expected_owner_ids) * 4),
                )
                verified_owner_ids = {
                    item.note.note_id
                    for item in related
                    if item.direction == "incoming"
                    and item.note.note_id in expected_owner_ids
                }
            except ObsidianDomainError as exc:
                graph_errors.append(_operation_error("graph_relation_lookup", exc))

        unresolved = tuple(sorted(expected_owner_ids.difference(verified_owner_ids)))
        graph = ObsidianReportBundleGraphResult(
            expected_incoming_edges=len(expected_owner_ids),
            verified_incoming_edges=len(verified_owner_ids),
            unresolved_links=unresolved,
        )
        if normalized.verify.incoming_edges and len(verified_owner_ids) != len(
            expected_owner_ids
        ):
            if not graph_errors:
                graph_errors.append(
                    {
                        "function": "graph_relation_lookup",
                        "message": "Expected graph owner edges were not found",
                    }
                )
            result = ObsidianReportBundleResult(
                completion_status=(
                    ObsidianReportBundleCompletionStatus.PARTIAL_GRAPH_UNVERIFIED
                ),
                idempotency_key=key,
                replayed=False,
                source=source_result,
                owner_writes=tuple(owner_writes),
                graph=graph,
                duplicates=duplicates,
                failed_stage="VERIFY_INCOMING_EDGES",
                errors=tuple(graph_errors),
            )
            self._save_checkpoint(store, normalized, request_hash, result)
            return result

        warnings: list[JSONObject] = []
        if duplicates:
            warnings.append(
                {
                    "function": "duplicate_verification",
                    "message": "Logical or content duplicates were found",
                    "paths": list(duplicates),
                }
            )
        if reindex_report.graph_projection.issue_total:
            warnings.append(
                {
                    "function": "graph_projection_rebuild",
                    "message": (
                        f"{reindex_report.graph_projection.issue_total} graph "
                        "projection issues were reported"
                    ),
                }
            )
        result = ObsidianReportBundleResult(
            completion_status=(
                ObsidianReportBundleCompletionStatus.COMPLETED_WITH_WARNINGS
                if warnings
                else ObsidianReportBundleCompletionStatus.COMPLETED
            ),
            idempotency_key=key,
            replayed=False,
            source=source_result,
            owner_writes=tuple(owner_writes),
            graph=graph,
            duplicates=duplicates,
            errors=tuple(warnings),
        )
        self._save_checkpoint(store, normalized, request_hash, result)
        return result

    def _normalized_request(
        self,
        request: ObsidianReportBundleRequest,
    ) -> ObsidianReportBundleRequest:
        root = self._vault_config_store.current().alexandria_root
        if request.source.relative_path is None:
            raise ObsidianValidationError("report bundle source.path is required")
        source = replace(
            request.source,
            relative_path=canonical_managed_note_path(
                request.source.relative_path,
                alexandria_root=root,
            ),
        )
        owners = tuple(
            replace(
                owner,
                path=canonical_managed_note_path(
                    owner.path,
                    alexandria_root=root,
                ),
            )
            for owner in request.graph_owners
        )
        if len({owner.path for owner in owners}) != len(owners):
            raise ObsidianValidationError("graph owner paths must be unique")
        return replace(request, source=source, graph_owners=owners)

    async def _duplicate_paths(
        self,
        request: ObsidianReportBundleRequest,
        source: ObsidianNote,
    ) -> tuple[str, ...]:
        """Find exact content or declared report-identity duplicates."""
        duplicates: set[str] = set()
        requested_path = request.source.relative_path
        if requested_path is not None and source.relative_path != requested_path:
            duplicates.add(source.relative_path)
        inventory = await self._obsidian_service.inventory_vault(
            ObsidianVaultInventoryRequest()
        )
        for item in inventory:
            if item.note_id == source.note_id:
                continue
            try:
                candidate = await self._obsidian_service.read_note(item.note_id)
            except ObsidianNotFoundError:
                continue
            if _same_content(source, candidate) or _same_report_identity(
                source,
                candidate,
            ):
                duplicates.add(candidate.relative_path)
        return tuple(sorted(duplicates))

    async def _update_owner(
        self,
        contract: ObsidianReportBundleOwner,
        owner: ObsidianNote,
        source: ObsidianNoteWriteResult,
    ) -> ObsidianNoteWriteResult:
        field_name = _relation_field(contract.relation)
        targets = _relation_targets(owner.frontmatter.get(field_name))
        if not any(
            target.get("id") == source.note.note_id
            or target.get("path") == source.note.relative_path
            for target in targets
            if isinstance(target, dict)
        ):
            targets.append(
                {
                    "id": source.note.note_id,
                    "path": source.note.relative_path,
                    "relation": contract.relation.value,
                }
            )
        payload = ObsidianSaveNote(
            title=owner.title,
            body=owner.body.removeprefix("\n"),
            alexandria_type=owner.alexandria_type,
            note_id=owner.note_id,
            relative_path=owner.relative_path,
            tags=owner.tags,
            status=owner.status,
            project=owner.project,
            source=owner.source or "report_bundle",
            frontmatter={field_name: targets},
            expected_content_hash=owner.content_hash,
        )
        return await self._obsidian_service.write_note(
            ObsidianWriteNote(
                note=payload,
                write_mode=ObsidianWriteMode.UPDATE,
                match_by=ObsidianWriteMatchBy.PATH,
                frontmatter_mode=ObsidianFrontmatterMode.MERGE,
            )
        )

    async def _completed_replay(
        self,
        request: ObsidianReportBundleRequest,
        checkpoint: JSONObject | None,
    ) -> ObsidianReportBundleResult | None:
        if checkpoint is None or checkpoint.get("completion_status") not in {
            ObsidianReportBundleCompletionStatus.COMPLETED.value,
            ObsidianReportBundleCompletionStatus.COMPLETED_WITH_WARNINGS.value,
        }:
            return None
        source_note_id = checkpoint.get("source_note_id")
        if not isinstance(source_note_id, str):
            return None
        try:
            note = await self._obsidian_service.read_note(source_note_id)
        except ObsidianNotFoundError:
            return None
        expected = _checkpoint_int(checkpoint, "expected_incoming_edges")
        verified = _checkpoint_int(checkpoint, "verified_incoming_edges")
        owner_writes: list[ObsidianNoteWriteResult] = []
        for owner_record in _checkpoint_dicts(checkpoint, "owner_writes"):
            note_id = owner_record.get("note_id")
            operation = owner_record.get("operation")
            if not isinstance(note_id, str) or not isinstance(operation, str):
                continue
            try:
                owner_note = await self._obsidian_service.read_note(note_id)
            except ObsidianNotFoundError:
                continue
            owner_writes.append(
                ObsidianNoteWriteResult(
                    operation=ObsidianWriteOperation(operation),
                    write_mode=ObsidianWriteMode.UPDATE,
                    match_by=ObsidianWriteMatchBy.PATH,
                    note=owner_note,
                    storage_status="unchanged",
                    metadata_status="indexed",
                    fts_status="indexed",
                    sqlite_graph_edge_status="indexed",
                    graph_projection_status="ready",
                    reindex_required=False,
                )
            )
        source = ObsidianNoteWriteResult(
            operation=ObsidianWriteOperation.UNCHANGED,
            write_mode=ObsidianWriteMode.UPSERT,
            match_by=ObsidianWriteMatchBy.PATH,
            note=note,
            storage_status="unchanged",
            metadata_status="indexed",
            fts_status="indexed",
            sqlite_graph_edge_status="indexed",
            graph_projection_status="ready",
            reindex_required=False,
        )
        return ObsidianReportBundleResult(
            completion_status=ObsidianReportBundleCompletionStatus(
                str(checkpoint["completion_status"])
            ),
            idempotency_key=request.idempotency_key,
            replayed=True,
            source=source,
            owner_writes=tuple(owner_writes),
            graph=ObsidianReportBundleGraphResult(
                expected_incoming_edges=expected,
                verified_incoming_edges=verified,
                unresolved_links=tuple(
                    _checkpoint_strings(checkpoint, "unresolved_links")
                ),
            ),
            duplicates=tuple(_checkpoint_strings(checkpoint, "duplicates")),
            failed_stage=_checkpoint_string(checkpoint, "failed_stage"),
            errors=tuple(_checkpoint_dicts(checkpoint, "errors")),
        )

    @staticmethod
    def _failure(
        *,
        request: ObsidianReportBundleRequest,
        status: ObsidianReportBundleCompletionStatus,
        stage: str,
        error: Exception,
        source: ObsidianNoteWriteResult | None = None,
        owner_writes: tuple[ObsidianNoteWriteResult, ...] = (),
    ) -> ObsidianReportBundleResult:
        return ObsidianReportBundleResult(
            completion_status=status,
            idempotency_key=request.idempotency_key,
            replayed=False,
            source=source,
            owner_writes=owner_writes,
            graph=ObsidianReportBundleGraphResult(
                expected_incoming_edges=len(request.graph_owners),
                verified_incoming_edges=0,
            ),
            failed_stage=stage,
            errors=(_operation_error(stage.lower(), error),),
        )

    @staticmethod
    def _save_checkpoint(
        store: ObsidianReportBundleRunStore,
        request: ObsidianReportBundleRequest,
        request_hash: str,
        result: ObsidianReportBundleResult,
    ) -> None:
        store.save(
            request.idempotency_key,
            {
                "request_hash": request_hash,
                "completion_status": result.completion_status.value,
                "failed_stage": result.failed_stage,
                "source_note_id": (
                    None if result.source is None else result.source.note.note_id
                ),
                "expected_incoming_edges": result.graph.expected_incoming_edges,
                "verified_incoming_edges": result.graph.verified_incoming_edges,
                "unresolved_links": list(result.graph.unresolved_links),
                "duplicates": list(result.duplicates),
                "errors": list(result.errors),
                "owner_writes": [
                    {
                        "note_id": item.note.note_id,
                        "operation": item.operation.value,
                    }
                    for item in result.owner_writes
                ],
            },
        )


def _request_hash(request: ObsidianReportBundleRequest) -> str:
    payload = {
        "source": {
            "title": request.source.title,
            "body": request.source.body,
            "alexandria_type": request.source.alexandria_type.value,
            "note_id": request.source.note_id,
            "path": request.source.relative_path,
            "tags": list(request.source.tags),
            "status": request.source.status,
            "project": request.source.project,
            "source": request.source.source,
            "frontmatter": request.source.frontmatter,
            "expected_content_hash": request.source.expected_content_hash,
        },
        "graph_owners": [
            {"path": owner.path, "relation": owner.relation.value}
            for owner in request.graph_owners
        ],
        "reindex": request.reindex,
        "verify": {
            "index_status": request.verify.index_status,
            "incoming_edges": request.verify.incoming_edges,
            "duplicates": request.verify.duplicates,
        },
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _relation_field(relation: ObsidianRelationType) -> str:
    if relation is ObsidianRelationType.CITES:
        return "source_ref_links"
    if relation is ObsidianRelationType.WIKILINK:
        raise ObsidianValidationError(
            "graph owner relation must be a managed frontmatter relation"
        )
    return relation.value


def _relation_targets(value: JSONValue | None) -> list[JSONValue]:
    if value is None:
        return []
    if isinstance(value, list):
        return list(value)
    return [value]


def _operation_error(function: str, error: Exception) -> JSONObject:
    return {"function": function, "message": str(error) or type(error).__name__}


def _checkpoint_int(checkpoint: JSONObject, key: str) -> int:
    value = checkpoint.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _checkpoint_string(checkpoint: JSONObject, key: str) -> str | None:
    value = checkpoint.get(key)
    return value if isinstance(value, str) else None


def _checkpoint_strings(checkpoint: JSONObject, key: str) -> list[str]:
    value = checkpoint.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _checkpoint_dicts(checkpoint: JSONObject, key: str) -> list[JSONObject]:
    value = checkpoint.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _same_content(left: ObsidianNote, right: ObsidianNote) -> bool:
    left_hash = left.frontmatter.get("content_hash")
    right_hash = right.frontmatter.get("content_hash")
    return isinstance(left_hash, str) and bool(left_hash) and left_hash == right_hash


def _same_report_identity(left: ObsidianNote, right: ObsidianNote) -> bool:
    fields = ("report_family", "report", "date", "entity", "edition")
    left_values = {
        field: _normalized_identity_value(left.frontmatter.get(field))
        for field in fields
    }
    right_values = {
        field: _normalized_identity_value(right.frontmatter.get(field))
        for field in fields
    }
    left_family = left_values["report_family"] or left_values["report"]
    right_family = right_values["report_family"] or right_values["report"]
    required = (left_family, left_values["date"], left_values["entity"])
    if not all(required):
        return False
    return (
        left_family == right_family
        and left_values["date"] == right_values["date"]
        and left_values["entity"] == right_values["entity"]
        and left_values["edition"] == right_values["edition"]
        and _normalized_identity_value(left.project)
        == _normalized_identity_value(right.project)
    )


# Broad type justified: canonical frontmatter values are JSON-compatible scalars.
def _normalized_identity_value(value: object) -> str:
    return " ".join(value.casefold().split()) if isinstance(value, str) else ""
