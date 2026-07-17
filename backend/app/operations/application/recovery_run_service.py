"""Manual operational recovery run execution service."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from shutil import disk_usage, move
from typing import Any, Protocol, cast

from app.memory.domain.entities.context_read_models import ContextReindexResult
from app.obsidian.domain.contracts.obsidian_contracts import ObsidianSearchQuery
from app.obsidian.domain.entities.obsidian_note import (
    ObsidianNote,
    ObsidianReindexResult,
    ObsidianSearchHit,
)
from app.operations.application.operational_readiness_service import (
    ContextReadinessService,
    ObsidianReadinessService,
    OperationalReadinessService,
)
from app.operations.application.recovery_plan_service import (
    RecoveryPlanRequest,
    RecoveryPlanService,
)
from app.operations.domain.entities.recovery_plan import (
    RecoveryPlan,
    RecoveryPlanStep,
    RecoveryQuarantineArtifactPlan,
    RecoverySourceSnapshot,
)
from app.operations.domain.entities.recovery_run import (
    RecoveryQuarantineInventoryItem,
    RecoveryRun,
    RecoveryRunStepResult,
)
from app.operations.domain.event_enum.operational_recovery_enums import (
    RecoveryRunStatus,
    RecoveryStepStatus,
)
from app.operations.domain.recovery_state_constants import (
    UNREADABLE_ACTIVE_RECOVERY_RUN_ID,
)
from app.shared.infrastructure.database import Database
from app.shared.serialization.orjson_codec import dumps_pretty_json, loads_json
from app.shared.types.extra_types import JSONObject


class ContextRecoveryService(ContextReadinessService, Protocol):
    """Context service subset used by recovery execution."""

    async def reindex_embeddings(
        self,
        limit: int = 100,
        *,
        force: bool = False,
    ) -> ContextReindexResult:
        """Rebuild retrieval embeddings.

        Args:
            limit: Maximum chunks to rebuild.
            force: Whether to rebuild existing embeddings.

        Returns:
            Context embedding reindex result.
        """


class ObsidianRecoveryService(ObsidianReadinessService, Protocol):
    """Obsidian service subset used by recovery execution."""

    async def reindex(self) -> ObsidianReindexResult:
        """Rebuild the Obsidian vault index.

        Returns:
            Obsidian reindex result.
        """

    async def search(
        self,
        query: ObsidianSearchQuery,
        *,
        refresh: bool = True,
    ) -> list[ObsidianSearchHit]:
        """Search indexed Obsidian notes.

        Args:
            query: Search query.
            refresh: Whether to refresh before searching.

        Returns:
            Matching Obsidian notes.
        """

    async def read_note(self, note_id: str) -> ObsidianNote:
        """Read one indexed Obsidian note by stable id.

        Args:
            note_id: Expected note identifier.

        Returns:
            Indexed Obsidian note.
        """

    async def read_note_by_path(self, relative_path: str) -> ObsidianNote:
        """Read one indexed Obsidian note by vault-relative path.

        Args:
            relative_path: Vault-relative note path.

        Returns:
            Indexed Obsidian note.
        """


StepCallable = Callable[[], Awaitable[JSONObject]]
_REPRESENTATIVE_QUERY = "운영 안정성 자동 복구 루프"
_REPRESENTATIVE_NOTE_ID = "prd_operational_readiness_recovery_v0_1"
_REPRESENTATIVE_PATH_SUFFIX = (
    "Contexts/Projects/alexandria-hermes/dev-size/PRD/"
    "PRD - 운영 안정성 및 자동 복구 루프.md"
)


class RecoveryInProgressError(RuntimeError):
    """Raised when a different recovery run is already active."""

    def __init__(self, *, run_id: str, idempotency_key: str | None) -> None:
        """Create error.

        Args:
            run_id: Active recovery run id.
            idempotency_key: Active recovery idempotency key when known.
        """
        super().__init__("recovery is already in progress")
        self.run_id = run_id
        self.idempotency_key = idempotency_key


class RecoveryStepFailedError(RuntimeError):
    """Raised when a recovery step result must fail the run."""

    def __init__(self, *, error_code: str, error_summary: str) -> None:
        """Create step failure.

        Args:
            error_code: PRD recovery error code.
            error_summary: Human-readable failure summary.
        """
        super().__init__(error_summary)
        self.error_code = error_code
        self.error_summary = error_summary


class RecoveryRunService:
    """Execute manual recovery runs after a safe dry-run plan."""

    def __init__(
        self,
        *,
        database: Database,
        context_service: ContextRecoveryService,
        obsidian_service: ObsidianRecoveryService,
    ) -> None:
        """Create service.

        Args:
            database: Shared database coordinator.
            context_service: Context/RAG service.
            obsidian_service: Obsidian vault service.
        """
        self._database = database
        self._context_service = context_service
        self._obsidian_service = obsidian_service

    async def start(self, request: RecoveryPlanRequest) -> RecoveryRun:
        """Start or return an idempotent manual recovery run.

        Args:
            request: Recovery plan/start request.

        Returns:
            Executed or previously stored recovery run.
        """
        plan = await RecoveryPlanService(
            database=self._database,
            context_service=self._context_service,
            obsidian_service=self._obsidian_service,
        ).plan(request)
        manifest_path = _manifest_path(plan)
        if manifest_path.exists():
            return _run_from_manifest(manifest_path)
        active_lock = _read_active_lock(self._database.sqlite_path)
        if active_lock is not None:
            raise RecoveryInProgressError(
                run_id=str(active_lock["run_id"]),
                idempotency_key=cast(str | None, active_lock.get("idempotency_key")),
            )
        if not plan.automatic_execution_allowed:
            run = _blocked_run(plan=plan, manifest_path=manifest_path)
            _write_manifest(run)
            return run

        parent_run = _parent_run_for_retry(
            database_path=self._database.sqlite_path,
            parent_run_id=request.parent_run_id,
        )
        parent_success_steps = _successful_parent_steps(parent_run)

        _write_active_lock(plan)
        started_at = datetime.now(UTC)
        step_results: list[RecoveryRunStepResult] = []
        rebuild_results: JSONObject = {}
        verification_results: JSONObject = {}
        error_code: str | None = None
        error_summary: str | None = None
        status = RecoveryRunStatus.RUNNING
        current_step: str | None = None
        try:
            current_step = _checkpoint_active_step(plan, "snapshot_sources")
            step_results.append(
                await _execute_or_skip_step(
                    current_step,
                    lambda: _snapshot_sources(plan),
                    parent_run=parent_run,
                    parent_success_steps=parent_success_steps,
                )
            )
            current_step = _checkpoint_active_step(plan, "dispose_connections")
            step_results.append(
                await _execute_or_skip_step(
                    current_step,
                    self._dispose_connections,
                    parent_run=parent_run,
                    parent_success_steps=parent_success_steps,
                )
            )
            current_step = _checkpoint_active_step(plan, "quarantine_sqlite_files")
            step_results.append(
                await _execute_or_skip_step(
                    current_step,
                    lambda: _quarantine_files(plan.quarantine_artifacts),
                    parent_run=parent_run,
                    parent_success_steps=parent_success_steps,
                )
            )
            current_step = _checkpoint_active_step(plan, "rebuild_database_schema")
            schema_result = await _execute_or_skip_step(
                current_step,
                self._rebuild_database,
                parent_run=parent_run,
                parent_success_steps=parent_success_steps,
            )
            step_results.append(schema_result)
            rebuild_results["schema"] = schema_result.result
            current_step = _checkpoint_active_step(plan, "reindex_vault")
            vault_result = await _execute_or_skip_step(
                current_step,
                self._reindex_vault,
                parent_run=parent_run,
                parent_success_steps=parent_success_steps,
            )
            step_results.append(vault_result)
            rebuild_results["vault"] = vault_result.result
            _require_step_success(vault_result, error_code="VAULT_REINDEX_FAILED")
            _require_empty_result_list(
                vault_result,
                key="errors",
                error_code="VAULT_REINDEX_FAILED",
            )
            current_step = _checkpoint_active_step(plan, "reindex_embeddings")
            embedding_result = await _execute_or_skip_step(
                current_step,
                self._reindex_embeddings,
                parent_run=parent_run,
                parent_success_steps=parent_success_steps,
            )
            step_results.append(embedding_result)
            rebuild_results["embeddings"] = embedding_result.result
            _require_step_success(
                embedding_result,
                error_code="EMBEDDING_REINDEX_FAILED",
            )
            _require_empty_result_list(
                embedding_result,
                key="warnings",
                error_code="EMBEDDING_REINDEX_REQUIRED",
            )
            current_step = _checkpoint_active_step(plan, "verify_readiness")
            verification_result = await _execute_or_skip_step(
                current_step,
                lambda: self._verify_readiness(plan),
                parent_run=parent_run,
                parent_success_steps=parent_success_steps,
            )
            step_results.append(verification_result)
            verification_results = verification_result.result
            status = (
                RecoveryRunStatus.COMPLETED
                if verification_results.get("ready") is True
                else RecoveryRunStatus.FAILED
            )
            if status is RecoveryRunStatus.FAILED:
                error_code = "READINESS_VERIFICATION_FAILED"
                error_summary = "Operational readiness did not become READY."
        except RecoveryStepFailedError as exc:
            status = RecoveryRunStatus.FAILED
            error_code = exc.error_code
            error_summary = exc.error_summary
        except Exception as exc:
            status = RecoveryRunStatus.FAILED
            error_code = "RECOVERY_RUN_FAILED"
            error_summary = str(exc)
        finished_at = datetime.now(UTC)
        run = RecoveryRun(
            id=plan.id,
            parent_run_id=plan.parent_run_id,
            idempotency_key=plan.idempotency_key,
            trigger=plan.trigger,
            actor=plan.actor,
            status=status,
            current_step=current_step,
            started_at=started_at,
            updated_at=finished_at,
            finished_at=finished_at,
            source_snapshot=plan.source_snapshot,
            diagnosis=plan.diagnosis,
            quarantine_artifacts=plan.quarantine_artifacts,
            planned_steps=plan.steps,
            step_results=step_results,
            rebuild_results=rebuild_results,
            verification_results=verification_results,
            error_code=error_code,
            error_summary=error_summary,
            next_actions=[]
            if status is RecoveryRunStatus.COMPLETED
            else ["inspect_recovery_run"],
            manifest_path=str(manifest_path),
        )
        _write_manifest(run)
        _clear_active_lock(plan)
        return run

    async def get(self, run_id: str) -> RecoveryRun | None:
        """Return a persisted recovery run by id.

        Args:
            run_id: Recovery run identifier.

        Returns:
            Recovery run from manifest, or None when it is unknown.
        """
        manifest_path = _manifest_path_by_id(
            database_path=self._database.sqlite_path,
            run_id=run_id,
        )
        if not manifest_path.exists():
            active_lock = _read_active_lock(self._database.sqlite_path)
            if active_lock is not None and active_lock.get("run_id") == run_id:
                vault_status = await self._obsidian_service.status()
                run = _interrupted_active_run(
                    database_path=self._database.sqlite_path,
                    active_lock=active_lock,
                    source_snapshot=_source_snapshot_from_vault(
                        vault_path=vault_status.vault_path,
                        alexandria_root=vault_status.alexandria_root,
                    ),
                    manifest_path=manifest_path,
                )
                _write_manifest(run)
                _clear_active_lock_for_run_id(
                    database_path=self._database.sqlite_path,
                    run_id=run_id,
                )
                return run
            return None
        return _run_from_manifest(manifest_path)

    async def retry(
        self,
        parent_run_id: str,
        request: RecoveryPlanRequest,
    ) -> RecoveryRun | None:
        """Start a parent-linked retry recovery run.

        Args:
            parent_run_id: Recovery run id to retry.
            request: Retry request input.

        Returns:
            New or idempotent retry run, or None when the parent is unknown.
        """
        parent_run = await self.get(parent_run_id)
        if parent_run is None:
            return None
        retry_request = RecoveryPlanRequest(
            trigger=request.trigger,
            actor=request.actor,
            idempotency_key=request.idempotency_key
            or _default_retry_idempotency_key(parent_run_id),
            parent_run_id=parent_run_id,
        )
        return await self.start(retry_request)

    async def quarantine_inventory(self) -> list[RecoveryQuarantineInventoryItem]:
        """Return quarantined artifact inventory for this database.

        Returns:
            Quarantine items recorded in persisted recovery run manifests.
        """
        recovery_dir = _recovery_dir(self._database.sqlite_path)
        if not recovery_dir.exists():
            return []
        items: list[RecoveryQuarantineInventoryItem] = []
        for manifest_path in sorted(recovery_dir.glob("*/recovery-run.json")):
            run = _run_from_manifest(manifest_path)
            for artifact in run.quarantine_artifacts:
                quarantine_path = Path(artifact.quarantine_path)
                items.append(
                    RecoveryQuarantineInventoryItem(
                        run_id=run.id,
                        run_status=run.status,
                        source_path=artifact.source_path,
                        quarantine_path=artifact.quarantine_path,
                        exists=quarantine_path.exists(),
                        size_bytes=(
                            quarantine_path.stat().st_size
                            if quarantine_path.exists()
                            else None
                        ),
                        sha256=artifact.sha256,
                    )
                )
        return items

    async def _dispose_connections(self) -> JSONObject:
        await self._database.engine.dispose()
        return {"disposed": True}

    async def _rebuild_database(self) -> JSONObject:
        await self._database.initialize()
        return {"initialized": True}

    async def _reindex_vault(self) -> JSONObject:
        result = await self._obsidian_service.reindex()
        return {
            "files_seen": result.files_seen,
            "files_indexed": result.files_indexed,
            "files_skipped": result.files_skipped,
            "stale_marked": result.stale_marked,
            "errors": result.errors,
        }

    async def _reindex_embeddings(self) -> JSONObject:
        result = await self._context_service.reindex_embeddings(limit=1000, force=True)
        return {
            "scanned": result.scanned,
            "updated": result.updated,
            "skipped": result.skipped,
            "warnings": result.warnings,
        }

    async def _verify_readiness(self, plan: RecoveryPlan) -> JSONObject:
        snapshot = await OperationalReadinessService(
            database=self._database,
            context_service=self._context_service,
            obsidian_service=self._obsidian_service,
            ignore_active_recovery_run_id=plan.id,
        ).snapshot()
        representative = await self._verify_representative_search()
        source_preservation = _source_preservation_result(plan.source_snapshot)
        warnings = list(snapshot.warnings)
        blockers = list(snapshot.blockers)
        if representative["matched"] is not True:
            warnings.append("representative_search_missing")
            blockers.append("representative_search_missing")
        if source_preservation["preserved"] is not True:
            warnings.append("source_markdown_changed")
            blockers.append("source_markdown_changed")
        return {
            "status": snapshot.status.value,
            "ready": (
                snapshot.ready
                and representative["matched"] is True
                and source_preservation["preserved"] is True
            ),
            "warnings": warnings,
            "blockers": blockers,
            "source_preservation": source_preservation,
            "representative_search": representative,
        }

    async def _verify_representative_search(self) -> JSONObject:
        hits = await self._obsidian_service.search(
            ObsidianSearchQuery(query=_REPRESENTATIVE_QUERY, limit=5),
            refresh=True,
        )
        matches: list[JSONObject] = [
            {
                "id": hit.note.note_id,
                "path": hit.note.relative_path,
                "title": hit.note.title,
            }
            for hit in hits
        ]
        matched_path = next(
            (
                str(match["path"])
                for match in matches
                if match["id"] == _REPRESENTATIVE_NOTE_ID
                and str(match["path"]).endswith(_REPRESENTATIVE_PATH_SUFFIX)
            ),
            None,
        )
        readback = await self._verify_representative_readback(matched_path)
        matched = matched_path is not None and readback["matched"] is True
        return {
            "query": _REPRESENTATIVE_QUERY,
            "expected_id": _REPRESENTATIVE_NOTE_ID,
            "expected_path_suffix": _REPRESENTATIVE_PATH_SUFFIX,
            "matched": matched,
            "matches": matches,
            "readback": readback,
        }

    async def _verify_representative_readback(
        self,
        matched_path: str | None,
    ) -> JSONObject:
        if matched_path is None:
            return {
                "matched": False,
                "id_read": None,
                "path_read": None,
                "error": None,
            }
        try:
            by_id = await self._obsidian_service.read_note(_REPRESENTATIVE_NOTE_ID)
            by_path = await self._obsidian_service.read_note_by_path(matched_path)
        except Exception as exc:  # pragma: no cover - exact read failures vary
            return {
                "matched": False,
                "id_read": None,
                "path_read": None,
                "error": str(exc),
            }
        id_read = _representative_readback_note_payload(by_id)
        path_read = _representative_readback_note_payload(by_path)
        return {
            "matched": (
                id_read["id"] == _REPRESENTATIVE_NOTE_ID
                and str(id_read["path"]).endswith(_REPRESENTATIVE_PATH_SUFFIX)
                and path_read["id"] == _REPRESENTATIVE_NOTE_ID
                and str(path_read["path"]).endswith(_REPRESENTATIVE_PATH_SUFFIX)
                and id_read["path"] == path_read["path"]
            ),
            "id_read": id_read,
            "path_read": path_read,
            "error": None,
        }


def _parent_run_for_retry(
    *, database_path: str | None, parent_run_id: str | None
) -> RecoveryRun | None:
    if parent_run_id is None:
        return None
    manifest_path = _manifest_path_by_id(
        database_path=database_path,
        run_id=parent_run_id,
    )
    if not manifest_path.exists():
        return None
    return _run_from_manifest(manifest_path)


def _successful_parent_steps(
    parent_run: RecoveryRun | None,
) -> dict[tuple[str, str], RecoveryRunStepResult]:
    if parent_run is None:
        return {}
    return {
        (step.code, step.input_hash): step
        for step in parent_run.step_results
        if step.status is RecoveryStepStatus.SUCCEEDED and step.input_hash
    }


def _representative_readback_note_payload(note: ObsidianNote) -> JSONObject:
    return {
        "id": note.note_id,
        "path": note.relative_path,
        "title": note.title,
        "content_hash": note.content_hash,
    }


async def _execute_or_skip_step(
    code: str,
    callback: StepCallable,
    *,
    parent_run: RecoveryRun | None,
    parent_success_steps: dict[tuple[str, str], RecoveryRunStepResult],
    input_payload: JSONObject | None = None,
) -> RecoveryRunStepResult:
    input_hash = _step_input_hash(code=code, input_payload=input_payload)
    parent_step = parent_success_steps.get((code, input_hash))
    if parent_run is not None and parent_step is not None:
        now = datetime.now(UTC)
        result: JSONObject = {
            **parent_step.result,
            "skipped_from_parent_run_id": parent_run.id,
            "skipped_parent_step_status": parent_step.status.value,
        }
        return RecoveryRunStepResult(
            code=code,
            status=RecoveryStepStatus.SKIPPED,
            attempts=0,
            started_at=now,
            finished_at=now,
            input_hash=input_hash,
            result=result,
        )
    return await _execute_step(code, callback, input_payload=input_payload)


async def _execute_step(
    code: str,
    callback: StepCallable,
    *,
    input_payload: JSONObject | None = None,
) -> RecoveryRunStepResult:
    started_at = datetime.now(UTC)
    input_hash = _step_input_hash(code=code, input_payload=input_payload)
    try:
        result = await callback()
        status = RecoveryStepStatus.SUCCEEDED
    except Exception as exc:
        result: JSONObject = {"error": str(exc)}
        status = RecoveryStepStatus.FAILED
        finished_at = datetime.now(UTC)
        return RecoveryRunStepResult(
            code,
            status,
            1,
            started_at,
            finished_at,
            input_hash,
            result,
        )
    finished_at = datetime.now(UTC)
    return RecoveryRunStepResult(
        code,
        status,
        1,
        started_at,
        finished_at,
        input_hash,
        result,
    )


def _step_input_hash(
    *,
    code: str,
    input_payload: JSONObject | None,
) -> str:
    payload: JSONObject = {"code": code, "input": input_payload or {}}
    return sha256(dumps_pretty_json(payload)).hexdigest()


def _require_step_success(
    step: RecoveryRunStepResult,
    *,
    error_code: str,
) -> None:
    if step.status in {RecoveryStepStatus.SUCCEEDED, RecoveryStepStatus.SKIPPED}:
        return
    raise RecoveryStepFailedError(
        error_code=error_code,
        error_summary=f"{step.code} failed",
    )


def _require_empty_result_list(
    step: RecoveryRunStepResult,
    *,
    key: str,
    error_code: str,
) -> None:
    value = step.result.get(key)
    if not isinstance(value, list) or not value:
        return
    details = ", ".join(str(item) for item in value)
    raise RecoveryStepFailedError(
        error_code=error_code,
        error_summary=f"{step.code} reported {key}: {details}",
    )


async def _snapshot_sources(plan: RecoveryPlan) -> JSONObject:
    return {
        "managed_markdown_count": plan.source_snapshot.managed_markdown_count,
        "representative_path": plan.source_snapshot.representative_path,
        "representative_sha256": plan.source_snapshot.representative_sha256,
        "markdown_manifest_count": len(plan.source_snapshot.markdown_manifest),
    }


def _source_snapshot_from_vault(
    *,
    vault_path: str,
    alexandria_root: str,
) -> RecoverySourceSnapshot:
    vault = Path(vault_path)
    root = Path(vault_path) / alexandria_root
    markdown_files = sorted(root.rglob("*.md")) if root.exists() else []
    representative = markdown_files[0] if markdown_files else None
    return RecoverySourceSnapshot(
        vault_path=vault_path,
        alexandria_root=alexandria_root,
        managed_markdown_count=len(markdown_files),
        representative_path=None if representative is None else str(representative),
        representative_sha256=_file_sha256(representative),
        disk_free_bytes=disk_usage(root).free if root.exists() else None,
        access_error=None,
        markdown_manifest=_markdown_manifest(vault, markdown_files),
    )


def _source_preservation_result(snapshot: RecoverySourceSnapshot) -> JSONObject:
    current_manifest = _current_markdown_manifest(snapshot)
    before_paths = set(snapshot.markdown_manifest)
    after_paths = set(current_manifest)
    removed_paths = sorted(before_paths - after_paths)
    added_paths = sorted(after_paths - before_paths)
    changed_paths = sorted(
        path
        for path in before_paths & after_paths
        if snapshot.markdown_manifest[path] != current_manifest[path]
    )
    return {
        "preserved": not removed_paths and not added_paths and not changed_paths,
        "managed_markdown_count": len(snapshot.markdown_manifest),
        "removed_count": len(removed_paths),
        "changed_count": len(changed_paths),
        "added_count": len(added_paths),
        "removed_paths": removed_paths,
        "changed_paths": changed_paths,
        "added_paths": added_paths,
    }


def _current_markdown_manifest(snapshot: RecoverySourceSnapshot) -> dict[str, str]:
    vault = Path(snapshot.vault_path)
    root = vault / snapshot.alexandria_root
    markdown_files = sorted(root.rglob("*.md")) if root.exists() else []
    return _markdown_manifest(vault, markdown_files)


def _markdown_manifest(vault: Path, markdown_files: list[Path]) -> dict[str, str]:
    return {
        str(path.relative_to(vault)): file_hash
        for path in markdown_files
        if (file_hash := _file_sha256(path)) is not None
    }


def _file_sha256(path: Path | None) -> str | None:
    if path is None or not path.exists() or not path.is_file():
        return None
    digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _quarantine_artifacts_for_run(
    *,
    database_path: str | None,
    run_id: str,
    created_at: datetime,
) -> list[RecoveryQuarantineArtifactPlan]:
    if database_path is None:
        return []
    timestamp = created_at.strftime("%Y%m%dT%H%M%SZ")
    source_paths = [
        Path(database_path),
        Path(f"{database_path}-wal"),
        Path(f"{database_path}-shm"),
    ]
    quarantine_dir = Path(database_path).parent / ".alexandria-recovery" / run_id
    return [
        RecoveryQuarantineArtifactPlan(
            source_path=str(source_path),
            quarantine_path=str(
                quarantine_dir / f"{timestamp}-{source_path.name}-{run_id}"
            ),
            exists=source_path.exists(),
            size_bytes=source_path.stat().st_size if source_path.exists() else None,
            sha256=_file_sha256(source_path) if source_path.exists() else None,
        )
        for source_path in source_paths
    ]


def _recovery_steps() -> list[RecoveryPlanStep]:
    return [
        RecoveryPlanStep("snapshot_sources", "Snapshot source vault metadata", False),
        RecoveryPlanStep("dispose_connections", "Dispose database connections", True),
        RecoveryPlanStep(
            "quarantine_sqlite_files", "Move SQLite files to quarantine", True
        ),
        RecoveryPlanStep(
            "rebuild_database_schema", "Rebuild migration-managed schema", True
        ),
        RecoveryPlanStep("reindex_vault", "Rebuild Obsidian index cache", True),
        RecoveryPlanStep("reindex_embeddings", "Rebuild retrieval embeddings", True),
        RecoveryPlanStep("verify_readiness", "Verify operational readiness", False),
    ]


async def _quarantine_files(
    artifacts: list[RecoveryQuarantineArtifactPlan],
) -> JSONObject:
    moved: list[JSONObject] = []
    for artifact in artifacts:
        if not artifact.exists:
            continue
        source = Path(artifact.source_path)
        destination = Path(artifact.quarantine_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        move(str(source), str(destination))
        moved.append(
            {
                "source_path": artifact.source_path,
                "quarantine_path": artifact.quarantine_path,
                "sha256": artifact.sha256,
                "size_bytes": artifact.size_bytes,
            }
        )
    return {"moved": moved}


def _blocked_run(*, plan: RecoveryPlan, manifest_path: Path) -> RecoveryRun:
    now = datetime.now(UTC)
    return RecoveryRun(
        id=plan.id,
        parent_run_id=plan.parent_run_id,
        idempotency_key=plan.idempotency_key,
        trigger=plan.trigger,
        actor=plan.actor,
        status=RecoveryRunStatus.BLOCKED,
        current_step=None,
        started_at=now,
        updated_at=now,
        finished_at=now,
        source_snapshot=plan.source_snapshot,
        diagnosis=plan.diagnosis,
        quarantine_artifacts=plan.quarantine_artifacts,
        planned_steps=plan.steps,
        step_results=[],
        rebuild_results={},
        verification_results={},
        error_code="RECOVERY_PLAN_BLOCKED",
        error_summary=", ".join(plan.blocked_reasons),
        next_actions=plan.next_actions,
        manifest_path=str(manifest_path),
    )


def _interrupted_active_run(
    *,
    database_path: str | None,
    active_lock: dict[str, Any],
    source_snapshot: RecoverySourceSnapshot,
    manifest_path: Path,
) -> RecoveryRun:
    started_at = _active_lock_started_at(active_lock) or datetime.now(UTC)
    now = datetime.now(UTC)
    return RecoveryRun(
        id=str(active_lock["run_id"]),
        parent_run_id=None,
        idempotency_key=cast(str, active_lock.get("idempotency_key") or ""),
        trigger=cast(str, active_lock.get("trigger") or "manual"),
        actor=cast(str, active_lock.get("actor") or "operator"),
        status=RecoveryRunStatus.BLOCKED,
        current_step=cast(str | None, active_lock.get("current_step")),
        started_at=started_at,
        updated_at=now,
        finished_at=now,
        source_snapshot=source_snapshot,
        diagnosis=["RECOVERY_INTERRUPTED_AFTER_RESTART"],
        quarantine_artifacts=_quarantine_artifacts_for_run(
            database_path=database_path,
            run_id=str(active_lock["run_id"]),
            created_at=started_at,
        ),
        planned_steps=_recovery_steps(),
        step_results=[],
        rebuild_results={},
        verification_results={},
        error_code="RECOVERY_INTERRUPTED_AFTER_RESTART",
        error_summary=(
            "Recovery active lock existed without a completed manifest; "
            "the run was blocked for operator retry after restart."
        ),
        next_actions=["retry_recovery_run", "inspect_recovery_run"],
        manifest_path=str(manifest_path),
    )


def _manifest_path(plan: RecoveryPlan) -> Path:
    return _manifest_path_by_id(
        database_path=plan.target_database_path,
        run_id=plan.id,
    )


def _manifest_path_by_id(*, database_path: str | None, run_id: str) -> Path:
    return _recovery_dir(database_path) / run_id / "recovery-run.json"


def _default_retry_idempotency_key(parent_run_id: str) -> str:
    return f"retry:{parent_run_id}"


def _recovery_dir(database_path: str | None) -> Path:
    if database_path is None:
        return Path.cwd() / ".alexandria-recovery"
    return Path(database_path).parent / ".alexandria-recovery"


def _active_lock_path(database_path: str | None) -> Path:
    return _recovery_dir(database_path) / "active-run.json"


def _read_active_lock(database_path: str | None) -> dict[str, Any] | None:
    path = _active_lock_path(database_path)
    if not path.exists():
        return None
    try:
        payload = loads_json(path.read_bytes())
    except (OSError, ValueError):
        return _unreadable_active_lock()
    if not isinstance(payload, dict) or "run_id" not in payload:
        return _unreadable_active_lock()
    return cast(dict[str, Any], payload)


def _unreadable_active_lock() -> dict[str, Any]:
    return {
        "run_id": UNREADABLE_ACTIVE_RECOVERY_RUN_ID,
        "idempotency_key": None,
        "read_error": "active_recovery_lock_unreadable",
    }


def _active_lock_started_at(active_lock: dict[str, Any]) -> datetime | None:
    value = active_lock.get("started_at")
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _write_active_lock(plan: RecoveryPlan) -> None:
    path = _active_lock_path(plan.target_database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: JSONObject = {
        "run_id": plan.id,
        "idempotency_key": plan.idempotency_key,
        "trigger": plan.trigger,
        "actor": plan.actor,
        "started_at": datetime.now(UTC).isoformat(),
    }
    path.write_bytes(dumps_pretty_json(payload))


def _checkpoint_active_step(plan: RecoveryPlan, current_step: str) -> str:
    path = _active_lock_path(plan.target_database_path)
    payload = _read_active_lock(plan.target_database_path)
    if payload is None or payload.get("run_id") != plan.id:
        payload = {
            "run_id": plan.id,
            "idempotency_key": plan.idempotency_key,
            "trigger": plan.trigger,
            "actor": plan.actor,
            "started_at": datetime.now(UTC).isoformat(),
        }
    payload["current_step"] = current_step
    payload["updated_at"] = datetime.now(UTC).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(dumps_pretty_json(cast(JSONObject, payload)))
    return current_step


def _clear_active_lock(plan: RecoveryPlan) -> None:
    path = _active_lock_path(plan.target_database_path)
    if not path.exists():
        return
    payload = _read_active_lock(plan.target_database_path)
    if payload is not None and payload.get("run_id") != plan.id:
        return
    path.unlink()


def _clear_active_lock_for_run_id(*, database_path: str | None, run_id: str) -> None:
    path = _active_lock_path(database_path)
    if not path.exists():
        return
    payload = _read_active_lock(database_path)
    if payload is None or payload.get("run_id") != run_id:
        return
    path.unlink()


def _write_manifest(run: RecoveryRun) -> None:
    path = Path(run.manifest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(dumps_pretty_json(_run_payload(run)))


def _run_from_manifest(path: Path) -> RecoveryRun:
    payload = loads_json(path.read_bytes())
    if not isinstance(payload, dict):
        raise ValueError("invalid recovery run manifest")
    return _run_from_payload(cast(dict[str, Any], payload), str(path))


def _run_payload(run: RecoveryRun) -> JSONObject:
    return {
        "id": run.id,
        "parent_run_id": run.parent_run_id,
        "idempotency_key": run.idempotency_key,
        "trigger": run.trigger,
        "actor": run.actor,
        "status": run.status.value,
        "current_step": run.current_step,
        "started_at": run.started_at.isoformat(),
        "updated_at": run.updated_at.isoformat(),
        "finished_at": None if run.finished_at is None else run.finished_at.isoformat(),
        "source_snapshot": _source_snapshot_payload(run.source_snapshot),
        "diagnosis": run.diagnosis,
        "quarantine_artifacts": [
            _artifact_payload(artifact) for artifact in run.quarantine_artifacts
        ],
        "planned_steps": [_planned_step_payload(step) for step in run.planned_steps],
        "step_results": [_step_result_payload(step) for step in run.step_results],
        "rebuild_results": run.rebuild_results,
        "verification_results": run.verification_results,
        "error_code": run.error_code,
        "error_summary": run.error_summary,
        "next_actions": run.next_actions,
    }


def _source_snapshot_payload(snapshot: RecoverySourceSnapshot) -> JSONObject:
    return {
        "vault_path": snapshot.vault_path,
        "alexandria_root": snapshot.alexandria_root,
        "managed_markdown_count": snapshot.managed_markdown_count,
        "representative_path": snapshot.representative_path,
        "representative_sha256": snapshot.representative_sha256,
        "disk_free_bytes": snapshot.disk_free_bytes,
        "access_error": snapshot.access_error,
        "markdown_manifest": cast(JSONObject, snapshot.markdown_manifest),
    }


def _artifact_payload(artifact: RecoveryQuarantineArtifactPlan) -> JSONObject:
    return {
        "source_path": artifact.source_path,
        "quarantine_path": artifact.quarantine_path,
        "exists": artifact.exists,
        "size_bytes": artifact.size_bytes,
        "sha256": artifact.sha256,
    }


def _planned_step_payload(step: RecoveryPlanStep) -> JSONObject:
    return {
        "code": step.code,
        "title": step.title,
        "mutates_state": step.mutates_state,
    }


def _step_result_payload(step: RecoveryRunStepResult) -> JSONObject:
    return {
        "code": step.code,
        "status": step.status.value,
        "attempts": step.attempts,
        "started_at": None if step.started_at is None else step.started_at.isoformat(),
        "finished_at": None
        if step.finished_at is None
        else step.finished_at.isoformat(),
        "input_hash": step.input_hash,
        "result": step.result,
    }


def _run_from_payload(payload: dict[str, Any], manifest_path: str) -> RecoveryRun:
    return RecoveryRun(
        id=str(payload["id"]),
        parent_run_id=cast(str | None, payload.get("parent_run_id")),
        idempotency_key=str(payload["idempotency_key"]),
        trigger=str(payload["trigger"]),
        actor=str(payload["actor"]),
        status=RecoveryRunStatus(str(payload["status"])),
        current_step=cast(str | None, payload.get("current_step")),
        started_at=datetime.fromisoformat(str(payload["started_at"])),
        updated_at=datetime.fromisoformat(str(payload["updated_at"])),
        finished_at=_optional_datetime(payload.get("finished_at")),
        source_snapshot=_source_snapshot_from_payload(
            cast(dict[str, Any], payload["source_snapshot"])
        ),
        diagnosis=[str(item) for item in cast(list[Any], payload.get("diagnosis", []))],
        quarantine_artifacts=[
            _artifact_from_payload(cast(dict[str, Any], item))
            for item in cast(list[Any], payload.get("quarantine_artifacts", []))
        ],
        planned_steps=[
            _planned_step_from_payload(cast(dict[str, Any], item))
            for item in cast(list[Any], payload.get("planned_steps", []))
        ],
        step_results=[
            _step_result_from_payload(cast(dict[str, Any], item))
            for item in cast(list[Any], payload.get("step_results", []))
        ],
        rebuild_results=cast(JSONObject, payload.get("rebuild_results", {})),
        verification_results=cast(JSONObject, payload.get("verification_results", {})),
        error_code=cast(str | None, payload.get("error_code")),
        error_summary=cast(str | None, payload.get("error_summary")),
        next_actions=[
            str(item) for item in cast(list[Any], payload.get("next_actions", []))
        ],
        manifest_path=manifest_path,
    )


def _optional_datetime(value: object) -> datetime | None:
    return None if value is None else datetime.fromisoformat(str(value))


def _source_snapshot_from_payload(payload: dict[str, Any]) -> RecoverySourceSnapshot:
    return RecoverySourceSnapshot(
        vault_path=str(payload["vault_path"]),
        alexandria_root=str(payload["alexandria_root"]),
        managed_markdown_count=int(payload["managed_markdown_count"]),
        representative_path=cast(str | None, payload.get("representative_path")),
        representative_sha256=cast(str | None, payload.get("representative_sha256")),
        disk_free_bytes=cast(int | None, payload.get("disk_free_bytes")),
        access_error=cast(str | None, payload.get("access_error")),
        markdown_manifest={
            str(key): str(value)
            for key, value in cast(
                dict[str, Any], payload.get("markdown_manifest", {})
            ).items()
        },
    )


def _artifact_from_payload(payload: dict[str, Any]) -> RecoveryQuarantineArtifactPlan:
    return RecoveryQuarantineArtifactPlan(
        source_path=str(payload["source_path"]),
        quarantine_path=str(payload["quarantine_path"]),
        exists=bool(payload["exists"]),
        size_bytes=cast(int | None, payload.get("size_bytes")),
        sha256=cast(str | None, payload.get("sha256")),
    )


def _planned_step_from_payload(payload: dict[str, Any]) -> RecoveryPlanStep:
    return RecoveryPlanStep(
        code=str(payload["code"]),
        title=str(payload["title"]),
        mutates_state=bool(payload["mutates_state"]),
    )


def _step_result_from_payload(payload: dict[str, Any]) -> RecoveryRunStepResult:
    return RecoveryRunStepResult(
        code=str(payload["code"]),
        status=RecoveryStepStatus(str(payload["status"])),
        attempts=int(payload["attempts"]),
        started_at=_optional_datetime(payload.get("started_at")),
        finished_at=_optional_datetime(payload.get("finished_at")),
        input_hash=str(payload.get("input_hash") or ""),
        result=cast(JSONObject, payload.get("result", {})),
    )
