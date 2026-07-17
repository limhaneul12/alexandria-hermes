"""Operational recovery run execution contracts."""

from __future__ import annotations

import sqlite3
from hashlib import sha256
from datetime import UTC, datetime
from pathlib import Path

import anyio
import app.connections.infrastructure.models.librarian_provider_models as _librarian_provider_models
import app.librarian.infrastructure.models.agent_models as _agent_models
import app.librarian.infrastructure.models.skill_acquisition_job_models as _skill_acquisition_job_models
import app.memory.infrastructure.models.context_models as _context_models
import app.obsidian.infrastructure.models.obsidian_index_models as _obsidian_index_models
from app.memory.domain.entities.context_read_models import (
    ContextReindexResult,
    RagDependencyHealth,
)
from app.memory.domain.event_enum.context_enums import RagHealthState, RagStrategy
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
from app.operations.application.recovery_plan_service import RecoveryPlanRequest
from app.operations.application.recovery_run_service import (
    RecoveryInProgressError,
    RecoveryRunService,
)
from app.operations.domain.event_enum.operational_recovery_enums import (
    RecoveryRunStatus,
)
from app.shared.infrastructure.database import Database
from app.shared.serialization.orjson_codec import dumps_pretty_json, loads_json

_ORM_MODELS_LOADED = (
    _agent_models,
    _context_models,
    _librarian_provider_models,
    _obsidian_index_models,
    _skill_acquisition_job_models,
)


class _FakeContextService:
    def __init__(
        self,
        *,
        embedding_warnings: list[str] | None = None,
        health_warnings: list[str] | None = None,
        default_strategy: RagStrategy = RagStrategy.HYBRID,
    ) -> None:
        self._embedding_warnings = embedding_warnings or []
        self._health_warnings = health_warnings or []
        self._default_strategy = default_strategy
        self.reindex_calls = 0

    async def rag_health_with_index_status(self) -> RagDependencyHealth:
        return RagDependencyHealth(
            fts=RagHealthState.HEALTHY,
            vector=RagHealthState.HEALTHY,
            embedding=RagHealthState.HEALTHY,
            default_strategy=self._default_strategy,
            model_name="test-model",
            dimensions=3,
            fingerprint={"provider": "test"},
            warnings=self._health_warnings,
        )

    async def reindex_embeddings(
        self, limit: int = 100, *, force: bool = False
    ) -> ContextReindexResult:
        self.reindex_calls += 1
        return ContextReindexResult(
            scanned=1,
            updated=1,
            skipped=0,
            warnings=self._embedding_warnings,
        )


class _FakeObsidianService:
    def __init__(
        self,
        vault: Path,
        *,
        representative_found: bool = True,
        representative_readback_matches: bool = True,
        reindex_errors: list[str] | None = None,
    ) -> None:
        self._vault = vault
        self._representative_found = representative_found
        self._representative_readback_matches = representative_readback_matches
        self._reindex_errors = reindex_errors or []
        self.reindex_calls = 0
        self.search_queries = []

    async def status(self) -> ObsidianVaultStatus:
        return ObsidianVaultStatus(
            vault_path=str(self._vault),
            alexandria_root="Alexandria",
            vault_exists=self._vault.exists(),
            alexandria_root_exists=(self._vault / "Alexandria").exists(),
            indexed_notes=1,
            stale_notes=0,
            error_notes=0,
        )

    async def reindex(self) -> ObsidianReindexResult:
        self.reindex_calls += 1
        return ObsidianReindexResult(
            files_seen=1,
            files_indexed=1,
            files_skipped=0,
            stale_marked=0,
            errors=self._reindex_errors,
        )

    async def search(self, query, *, refresh: bool = True):  # type: ignore[no-untyped-def]
        self.search_queries.append((query, refresh))
        if not self._representative_found:
            return []
        note = ObsidianNote(
            note_id="prd_operational_readiness_recovery_v0_1",
            relative_path=(
                "Contexts/Projects/alexandria-hermes/dev-size/PRD/"
                "PRD - 운영 안정성 및 자동 복구 루프.md"
            ),
            alexandria_type=AlexandriaNoteType.CONTEXT,
            title="PRD - 운영 안정성 및 자동 복구 루프",
            status="active",
            tags=[],
            project="alexandria-hermes",
            source="test",
            content_hash="hash",
            frontmatter={},
            body="# 운영 안정성 자동 복구 루프\n",
            index_status=ObsidianIndexStatus.INDEXED,
            error_message=None,
            size_bytes=100,
            modified_at=datetime(2026, 7, 16, 12, 0, tzinfo=UTC),
            indexed_at=datetime(2026, 7, 16, 12, 0, tzinfo=UTC),
        )
        return [
            ObsidianSearchHit(
                note=note,
                excerpt="운영 안정성 자동 복구 루프",
                score=1.0,
            )
        ]

    async def read_note(self, note_id: str) -> ObsidianNote:
        return self._representative_note()

    async def read_note_by_path(self, relative_path: str) -> ObsidianNote:
        return self._representative_note()

    def _representative_note(self) -> ObsidianNote:
        relative_path = (
            "Contexts/Projects/alexandria-hermes/dev-size/PRD/"
            "PRD - 운영 안정성 및 자동 복구 루프.md"
        )
        if not self._representative_readback_matches:
            relative_path = "Contexts/Projects/alexandria-hermes/dev-size/PRD/wrong.md"
        return ObsidianNote(
            note_id="prd_operational_readiness_recovery_v0_1",
            relative_path=relative_path,
            alexandria_type=AlexandriaNoteType.CONTEXT,
            title="PRD - 운영 안정성 및 자동 복구 루프",
            status="active",
            tags=[],
            project="alexandria-hermes",
            source="test",
            content_hash="hash",
            frontmatter={},
            body="# 운영 안정성 자동 복구 루프\n",
            index_status=ObsidianIndexStatus.INDEXED,
            error_message=None,
            size_bytes=100,
            modified_at=datetime(2026, 7, 16, 12, 0, tzinfo=UTC),
            indexed_at=datetime(2026, 7, 16, 12, 0, tzinfo=UTC),
        )


def _seed_corrupt_runtime(tmp_path: Path) -> tuple[Path, Path, bytes]:
    database_path = tmp_path / "corrupt.db"
    database_path.write_bytes(b"not a sqlite database")
    (tmp_path / "corrupt.db-wal").write_bytes(b"wal")
    (tmp_path / "corrupt.db-shm").write_bytes(b"shm")
    note = tmp_path / "vault" / "Alexandria" / "note.md"
    note.parent.mkdir(parents=True)
    note_body = b"# Note\n"
    note.write_bytes(note_body)
    return database_path, note, note_body


def _markdown_hashes(vault: Path) -> dict[str, str]:
    return {
        str(path.relative_to(vault)): sha256(path.read_bytes()).hexdigest()
        for path in sorted(vault.rglob("*.md"))
    }


def test_recovery_run_quarantines_sqlite_files_rebuilds_db_and_preserves_vault(
    tmp_path: Path,
) -> None:
    """Recovery run should move SQLite files, create a new DB, and not edit Markdown."""

    async def scenario() -> tuple[
        str,
        bool,
        bool,
        list[str],
        bytes,
        int,
        int,
        bool,
        object,
        list[tuple[object, bool]],
    ]:
        database_path, note, note_body = _seed_corrupt_runtime(tmp_path)
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        context_service = _FakeContextService()
        obsidian_service = _FakeObsidianService(tmp_path / "vault")
        service = RecoveryRunService(
            database=database,
            context_service=context_service,
            obsidian_service=obsidian_service,
        )

        run = await service.start(
            RecoveryPlanRequest(
                trigger="manual",
                actor="pytest",
                idempotency_key="run-key-1",
            )
        )
        table_names = (
            sqlite3.connect(database_path)
            .execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            .fetchall()
        )

        return (
            run.status,
            database_path.exists(),
            note.read_bytes() == note_body,
            [
                artifact.quarantine_path
                for artifact in run.quarantine_artifacts
                if artifact.exists
            ],
            (tmp_path / "corrupt.db").read_bytes(),
            context_service.reindex_calls,
            len(table_names),
            (tmp_path / ".alexandria-recovery" / "active-run.json").exists(),
            run.verification_results.get("representative_search"),
            obsidian_service.search_queries,
        )

    (
        status,
        db_exists,
        note_preserved,
        quarantine_paths,
        db_bytes,
        reindex_calls,
        table_count,
        active_lock_exists,
        representative_search,
        search_queries,
    ) = anyio.run(scenario)

    assert status == RecoveryRunStatus.COMPLETED
    assert db_exists is True
    assert note_preserved is True
    assert len(quarantine_paths) == 3
    assert all(Path(path).exists() for path in quarantine_paths)
    assert db_bytes != b"not a sqlite database"
    assert reindex_calls == 1
    assert table_count > 0
    assert active_lock_exists is False
    assert representative_search["matched"] is True
    search_query, refresh = search_queries[0]
    assert search_query.query == "운영 안정성 자동 복구 루프"
    assert refresh is True


def test_recovery_run_verifies_all_markdown_paths_and_hashes_are_preserved(
    tmp_path: Path,
) -> None:
    """Recovery verification should prove every managed Markdown file is unchanged."""

    async def scenario() -> tuple[str, object, dict[str, str], dict[str, str]]:
        database_path = tmp_path / "corrupt.db"
        database_path.write_bytes(b"not a sqlite database")
        (tmp_path / "corrupt.db-wal").write_bytes(b"wal")
        (tmp_path / "corrupt.db-shm").write_bytes(b"shm")
        vault = tmp_path / "vault"
        note_bodies = {
            "Alexandria/Contexts/Projects/project-a.md": b"# Project A\n",
            "Alexandria/Contexts/Projects/project-b.md": b"# Project B\n",
            "Alexandria/Skills/Drafts/http-skill.md": b"# HTTP Skill\n",
        }
        for relative_path, body in note_bodies.items():
            note_path = vault / relative_path
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_bytes(body)
        before_hashes = _markdown_hashes(vault)
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        service = RecoveryRunService(
            database=database,
            context_service=_FakeContextService(),
            obsidian_service=_FakeObsidianService(vault),
        )

        run = await service.start(
            RecoveryPlanRequest(
                trigger="manual",
                actor="pytest",
                idempotency_key="run-key-source-preservation",
            )
        )

        return (
            run.status,
            run.verification_results.get("source_preservation"),
            before_hashes,
            _markdown_hashes(vault),
        )

    status, source_preservation, before_hashes, after_hashes = anyio.run(scenario)

    assert status == RecoveryRunStatus.COMPLETED
    assert source_preservation == {
        "preserved": True,
        "managed_markdown_count": 3,
        "removed_count": 0,
        "changed_count": 0,
        "added_count": 0,
        "removed_paths": [],
        "changed_paths": [],
        "added_paths": [],
    }
    assert after_hashes == before_hashes


def test_recovery_run_fails_closed_when_markdown_source_changes_during_recovery(
    tmp_path: Path,
) -> None:
    """Recovery should not complete if managed Markdown changes during repair."""

    class _MutatingObsidianService(_FakeObsidianService):
        def __init__(self, vault: Path, *, target: Path) -> None:
            super().__init__(vault)
            self._target = target

        async def reindex(self) -> ObsidianReindexResult:
            result = await super().reindex()
            self._target.write_bytes(b"# Project A changed during recovery\n")
            return result

    async def scenario() -> tuple[str, list[str], object]:
        database_path = tmp_path / "corrupt.db"
        database_path.write_bytes(b"not a sqlite database")
        (tmp_path / "corrupt.db-wal").write_bytes(b"wal")
        (tmp_path / "corrupt.db-shm").write_bytes(b"shm")
        vault = tmp_path / "vault"
        target = vault / "Alexandria" / "Contexts" / "Projects" / "project-a.md"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"# Project A\n")
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        service = RecoveryRunService(
            database=database,
            context_service=_FakeContextService(),
            obsidian_service=_MutatingObsidianService(vault, target=target),
        )

        run = await service.start(
            RecoveryPlanRequest(
                trigger="manual",
                actor="pytest",
                idempotency_key="run-key-source-preservation-fails",
            )
        )
        return (
            run.status,
            list(run.verification_results.get("warnings", [])),
            run.verification_results.get("source_preservation"),
        )

    status, warnings, source_preservation = anyio.run(scenario)

    assert status == RecoveryRunStatus.FAILED
    assert "source_markdown_changed" in warnings
    assert source_preservation == {
        "preserved": False,
        "managed_markdown_count": 1,
        "removed_count": 0,
        "changed_count": 1,
        "added_count": 0,
        "removed_paths": [],
        "changed_paths": ["Alexandria/Contexts/Projects/project-a.md"],
        "added_paths": [],
    }


def test_recovery_run_records_full_rebuild_sequence_and_results(
    tmp_path: Path,
) -> None:
    """RecoveryRun should persist schema, vault, embedding, and verify outputs."""

    async def scenario() -> tuple[
        list[str],
        dict[str, object],
        dict[str, object],
        list[str],
    ]:
        database_path, _note, _note_body = _seed_corrupt_runtime(tmp_path)
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        service = RecoveryRunService(
            database=database,
            context_service=_FakeContextService(),
            obsidian_service=_FakeObsidianService(tmp_path / "vault"),
        )

        run = await service.start(
            RecoveryPlanRequest(
                trigger="manual",
                actor="pytest",
                idempotency_key="run-key-full-sequence",
            )
        )
        manifest = loads_json(Path(run.manifest_path).read_bytes())
        assert isinstance(manifest, dict)
        return (
            [step.code for step in run.step_results],
            run.rebuild_results,
            manifest["rebuild_results"],
            [step["code"] for step in manifest["step_results"]],
        )

    steps, rebuild_results, manifest_rebuild_results, manifest_steps = anyio.run(
        scenario
    )

    assert steps == [
        "snapshot_sources",
        "dispose_connections",
        "quarantine_sqlite_files",
        "rebuild_database_schema",
        "reindex_vault",
        "reindex_embeddings",
        "verify_readiness",
    ]
    assert manifest_steps == steps
    assert rebuild_results == {
        "schema": {"initialized": True},
        "vault": {
            "files_seen": 1,
            "files_indexed": 1,
            "files_skipped": 0,
            "stale_marked": 0,
            "errors": [],
        },
        "embeddings": {
            "scanned": 1,
            "updated": 1,
            "skipped": 0,
            "warnings": [],
        },
    }
    assert manifest_rebuild_results == rebuild_results


def test_recovery_run_fails_closed_when_vault_reindex_reports_errors(
    tmp_path: Path,
) -> None:
    """Recovery should stop before embeddings when vault reindex reports errors."""

    async def scenario() -> tuple[str, str | None, int, int, list[tuple[str, str]]]:
        database_path, _note, _note_body = _seed_corrupt_runtime(tmp_path)
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        context_service = _FakeContextService()
        obsidian_service = _FakeObsidianService(
            tmp_path / "vault",
            reindex_errors=["failed to index note.md"],
        )
        service = RecoveryRunService(
            database=database,
            context_service=context_service,
            obsidian_service=obsidian_service,
        )

        run = await service.start(
            RecoveryPlanRequest(
                trigger="manual",
                actor="pytest",
                idempotency_key="run-key-vault-reindex-error",
            )
        )
        return (
            run.status,
            run.error_code,
            obsidian_service.reindex_calls,
            context_service.reindex_calls,
            [(step.code, step.status.value) for step in run.step_results],
        )

    status, error_code, vault_calls, embedding_calls, steps = anyio.run(scenario)

    assert status == RecoveryRunStatus.FAILED
    assert error_code == "VAULT_REINDEX_FAILED"
    assert vault_calls == 1
    assert embedding_calls == 0
    assert steps[-1] == ("reindex_vault", "SUCCEEDED")


def test_recovery_run_fails_closed_when_embedding_reindex_reports_warnings(
    tmp_path: Path,
) -> None:
    """Recovery should not verify readiness when embedding reindex has warnings."""

    async def scenario() -> tuple[str, str | None, int, list[tuple[str, str]]]:
        database_path, _note, _note_body = _seed_corrupt_runtime(tmp_path)
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        context_service = _FakeContextService(
            embedding_warnings=["embedding fingerprint mismatch"]
        )
        obsidian_service = _FakeObsidianService(tmp_path / "vault")
        service = RecoveryRunService(
            database=database,
            context_service=context_service,
            obsidian_service=obsidian_service,
        )

        run = await service.start(
            RecoveryPlanRequest(
                trigger="manual",
                actor="pytest",
                idempotency_key="run-key-embedding-warning",
            )
        )
        return (
            run.status,
            run.error_code,
            context_service.reindex_calls,
            [(step.code, step.status.value) for step in run.step_results],
        )

    status, error_code, embedding_calls, steps = anyio.run(scenario)

    assert status == RecoveryRunStatus.FAILED
    assert error_code == "EMBEDDING_REINDEX_REQUIRED"
    assert embedding_calls == 1
    assert steps[-1] == ("reindex_embeddings", "SUCCEEDED")


def test_recovery_run_fails_closed_when_post_recovery_rag_has_warnings(
    tmp_path: Path,
) -> None:
    """Recovery should not complete while RAG health still reports warnings."""

    async def scenario() -> tuple[str, str | None, list[str], list[str]]:
        database_path, _note, _note_body = _seed_corrupt_runtime(tmp_path)
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        context_service = _FakeContextService(
            health_warnings=["vector index warning remains"]
        )
        obsidian_service = _FakeObsidianService(tmp_path / "vault")
        service = RecoveryRunService(
            database=database,
            context_service=context_service,
            obsidian_service=obsidian_service,
        )

        run = await service.start(
            RecoveryPlanRequest(
                trigger="manual",
                actor="pytest",
                idempotency_key="run-key-rag-warning",
            )
        )
        return (
            run.status,
            run.error_code,
            list(run.verification_results.get("warnings", [])),
            run.next_actions,
        )

    status, error_code, warnings, next_actions = anyio.run(scenario)

    assert status == RecoveryRunStatus.FAILED
    assert error_code == "READINESS_VERIFICATION_FAILED"
    assert warnings == ["rag_status_warnings_present"]
    assert next_actions == ["inspect_recovery_run"]


def test_recovery_run_fails_closed_when_post_recovery_strategy_is_not_hybrid(
    tmp_path: Path,
) -> None:
    """Recovery should not complete unless RAG default strategy is HYBRID."""

    async def scenario() -> tuple[str, str | None, list[str]]:
        database_path, _note, _note_body = _seed_corrupt_runtime(tmp_path)
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        context_service = _FakeContextService(default_strategy=RagStrategy.FTS_ONLY)
        obsidian_service = _FakeObsidianService(tmp_path / "vault")
        service = RecoveryRunService(
            database=database,
            context_service=context_service,
            obsidian_service=obsidian_service,
        )

        run = await service.start(
            RecoveryPlanRequest(
                trigger="manual",
                actor="pytest",
                idempotency_key="run-key-fts-only",
            )
        )
        return (
            run.status,
            run.error_code,
            list(run.verification_results.get("warnings", [])),
        )

    status, error_code, warnings = anyio.run(scenario)

    assert status == RecoveryRunStatus.FAILED
    assert error_code == "READINESS_VERIFICATION_FAILED"
    assert warnings == ["rag_default_strategy_not_hybrid"]


def test_recovery_run_fails_closed_when_representative_search_is_missing(
    tmp_path: Path,
) -> None:
    """Recovery should not complete when the representative PRD is not searchable."""

    async def scenario() -> tuple[str, object, str | None, list[str]]:
        database_path, _note, _note_body = _seed_corrupt_runtime(tmp_path)
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        context_service = _FakeContextService()
        obsidian_service = _FakeObsidianService(
            tmp_path / "vault",
            representative_found=False,
        )
        service = RecoveryRunService(
            database=database,
            context_service=context_service,
            obsidian_service=obsidian_service,
        )

        run = await service.start(
            RecoveryPlanRequest(
                trigger="manual",
                actor="pytest",
                idempotency_key="run-key-representative-missing",
            )
        )
        return (
            run.status,
            run.verification_results.get("representative_search"),
            run.error_code,
            run.next_actions,
        )

    status, representative_search, error_code, next_actions = anyio.run(scenario)

    assert status == RecoveryRunStatus.FAILED
    assert representative_search["matched"] is False
    assert error_code == "READINESS_VERIFICATION_FAILED"
    assert next_actions == ["inspect_recovery_run"]


def test_recovery_run_fails_closed_when_representative_readback_differs(
    tmp_path: Path,
) -> None:
    """Recovery should read back the representative PRD by id/path after search."""

    async def scenario() -> tuple[str, object, str | None, list[str]]:
        database_path, _note, _note_body = _seed_corrupt_runtime(tmp_path)
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        context_service = _FakeContextService()
        obsidian_service = _FakeObsidianService(
            tmp_path / "vault",
            representative_readback_matches=False,
        )
        service = RecoveryRunService(
            database=database,
            context_service=context_service,
            obsidian_service=obsidian_service,
        )

        run = await service.start(
            RecoveryPlanRequest(
                trigger="manual",
                actor="pytest",
                idempotency_key="run-key-representative-readback-differs",
            )
        )
        return (
            run.status,
            run.verification_results.get("representative_search"),
            run.error_code,
            run.next_actions,
        )

    status, representative_search, error_code, next_actions = anyio.run(scenario)

    assert status == RecoveryRunStatus.FAILED
    assert representative_search["matched"] is False
    assert representative_search["readback"]["matched"] is False
    assert error_code == "READINESS_VERIFICATION_FAILED"
    assert next_actions == ["inspect_recovery_run"]


def test_recovery_run_is_idempotent_for_existing_manifest(tmp_path: Path) -> None:
    """Same idempotency key should return the manifest without re-running mutation."""

    async def scenario() -> tuple[str, str, int, int]:
        database_path, _note, _note_body = _seed_corrupt_runtime(tmp_path)
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        context_service = _FakeContextService()
        obsidian_service = _FakeObsidianService(tmp_path / "vault")
        service = RecoveryRunService(
            database=database,
            context_service=context_service,
            obsidian_service=obsidian_service,
        )
        request = RecoveryPlanRequest(
            trigger="manual",
            actor="pytest",
            idempotency_key="same-key",
        )

        first = await service.start(request)
        second = await service.start(request)
        return (
            first.id,
            second.id,
            obsidian_service.reindex_calls,
            context_service.reindex_calls,
        )

    first_id, second_id, obsidian_calls, context_calls = anyio.run(scenario)

    assert first_id == second_id
    assert obsidian_calls == 1
    assert context_calls == 1


def test_recovery_run_lookup_reads_persisted_manifest_by_id(tmp_path: Path) -> None:
    """Run lookup should recover the persisted manifest without re-running steps."""

    async def scenario() -> tuple[str, str | None, int, int]:
        database_path, _note, _note_body = _seed_corrupt_runtime(tmp_path)
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        context_service = _FakeContextService()
        obsidian_service = _FakeObsidianService(tmp_path / "vault")
        service = RecoveryRunService(
            database=database,
            context_service=context_service,
            obsidian_service=obsidian_service,
        )
        created = await service.start(
            RecoveryPlanRequest(
                trigger="manual",
                actor="pytest",
                idempotency_key="lookup-key",
            )
        )
        loaded = await service.get(created.id)

        return (
            created.id,
            None if loaded is None else loaded.id,
            obsidian_service.reindex_calls,
            context_service.reindex_calls,
        )

    created_id, loaded_id, obsidian_calls, context_calls = anyio.run(scenario)

    assert loaded_id == created_id
    assert obsidian_calls == 1
    assert context_calls == 1


def test_recovery_run_lookup_returns_none_for_unknown_id(tmp_path: Path) -> None:
    """Unknown run ids should not invent recovery state."""

    async def scenario() -> bool:
        database = Database(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'runtime.db'}",
            create_schema=True,
        )
        service = RecoveryRunService(
            database=database,
            context_service=_FakeContextService(),
            obsidian_service=_FakeObsidianService(tmp_path / "vault"),
        )

        loaded = await service.get("missing-run")
        return loaded is None

    assert anyio.run(scenario) is True


def test_recovery_run_updates_active_lock_current_step_during_execution(
    tmp_path: Path,
) -> None:
    """Active lock should checkpoint the current safe recovery step."""

    class _LockInspectingObsidianService(_FakeObsidianService):
        def __init__(self, vault: Path, *, active_lock_path: Path) -> None:
            super().__init__(vault)
            self._active_lock_path = active_lock_path
            self.observed_current_step: str | None = None

        async def reindex(self) -> ObsidianReindexResult:
            payload = loads_json(self._active_lock_path.read_bytes())
            assert isinstance(payload, dict)
            current_step = payload.get("current_step")
            self.observed_current_step = (
                current_step if isinstance(current_step, str) else None
            )
            return await super().reindex()

    async def scenario() -> str | None:
        database_path, _, _ = _seed_corrupt_runtime(tmp_path)
        active_lock_path = tmp_path / ".alexandria-recovery" / "active-run.json"
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        obsidian_service = _LockInspectingObsidianService(
            tmp_path / "vault",
            active_lock_path=active_lock_path,
        )
        service = RecoveryRunService(
            database=database,
            context_service=_FakeContextService(),
            obsidian_service=obsidian_service,
        )

        await service.start(
            RecoveryPlanRequest(
                trigger="manual",
                actor="pytest",
                idempotency_key="run-key-checkpoint-step",
            )
        )
        return obsidian_service.observed_current_step

    assert anyio.run(scenario) == "reindex_vault"


def test_recovery_run_lookup_restores_interrupted_active_lock_as_blocked(
    tmp_path: Path,
) -> None:
    """After restart, an active lock without a manifest should become inspectable."""

    async def scenario() -> tuple[str, str | None, str | None, bool, bool]:
        database_path = tmp_path / "runtime.db"
        vault_root = tmp_path / "vault" / "Alexandria"
        vault_root.mkdir(parents=True)
        (vault_root / "note.md").write_text("# Note\n", encoding="utf-8")
        recovery_dir = tmp_path / ".alexandria-recovery"
        recovery_dir.mkdir()
        active_lock_path = recovery_dir / "active-run.json"
        active_lock_path.write_bytes(
            dumps_pretty_json(
                {
                    "run_id": "interrupted-run",
                    "idempotency_key": "interrupted-key",
                    "trigger": "manual",
                    "actor": "pytest",
                    "current_step": "reindex_vault",
                    "started_at": "2026-07-16T12:00:00+00:00",
                }
            )
        )
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        service = RecoveryRunService(
            database=database,
            context_service=_FakeContextService(),
            obsidian_service=_FakeObsidianService(tmp_path / "vault"),
        )

        run = await service.get("interrupted-run")

        assert run is not None
        return (
            run.status,
            run.error_code,
            run.current_step,
            active_lock_path.exists(),
            Path(run.manifest_path).exists(),
        )

    status, error_code, current_step, active_lock_exists, manifest_exists = anyio.run(
        scenario
    )

    assert status == RecoveryRunStatus.BLOCKED
    assert error_code == "RECOVERY_INTERRUPTED_AFTER_RESTART"
    assert current_step == "reindex_vault"
    assert active_lock_exists is False
    assert manifest_exists is True


def test_recovery_run_retry_creates_child_run_for_blocked_parent(
    tmp_path: Path,
) -> None:
    """Retry should create a new run linked to the original failed/blocked run."""

    async def scenario() -> tuple[str, str | None, str, str, int]:
        database_path = tmp_path / "corrupt.db"
        database_path.write_bytes(b"not a sqlite database")
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        context_service = _FakeContextService()
        obsidian_service = _FakeObsidianService(tmp_path / "vault")
        service = RecoveryRunService(
            database=database,
            context_service=context_service,
            obsidian_service=obsidian_service,
        )
        parent = await service.start(
            RecoveryPlanRequest(
                trigger="manual",
                actor="pytest",
                idempotency_key="blocked-parent-key",
            )
        )

        note = tmp_path / "vault" / "Alexandria" / "note.md"
        note.parent.mkdir(parents=True)
        note.write_text("# Note\n", encoding="utf-8")
        retry = await service.retry(
            parent.id,
            RecoveryPlanRequest(
                trigger="retry",
                actor="pytest",
                idempotency_key="child-retry-key",
            ),
        )
        assert retry is not None

        return (
            retry.status,
            retry.parent_run_id,
            parent.id,
            retry.id,
            context_service.reindex_calls,
        )

    status, parent_run_id, parent_id, retry_id, reindex_calls = anyio.run(scenario)

    assert status == RecoveryRunStatus.COMPLETED
    assert parent_run_id == parent_id
    assert retry_id != parent_id
    assert reindex_calls == 1


def test_recovery_run_retry_skips_parent_success_step_with_same_input_hash(
    tmp_path: Path,
) -> None:
    """Retry should skip parent-successful steps when the input hash matches."""

    async def scenario() -> tuple[str, str, int, object]:
        database_path, _note, _note_body = _seed_corrupt_runtime(tmp_path)
        parent_run_id = "parent-with-snapshot"
        snapshot_input_hash = sha256(
            dumps_pretty_json({"code": "snapshot_sources", "input": {}})
        ).hexdigest()
        recovery_dir = tmp_path / ".alexandria-recovery" / parent_run_id
        recovery_dir.mkdir(parents=True)
        (recovery_dir / "recovery-run.json").write_bytes(
            dumps_pretty_json(
                {
                    "id": parent_run_id,
                    "parent_run_id": None,
                    "idempotency_key": "parent-snapshot-key",
                    "trigger": "manual",
                    "actor": "pytest",
                    "status": "FAILED",
                    "current_step": "snapshot_sources",
                    "started_at": "2026-07-16T12:00:00+00:00",
                    "updated_at": "2026-07-16T12:00:01+00:00",
                    "finished_at": "2026-07-16T12:00:01+00:00",
                    "source_snapshot": {
                        "vault_path": str(tmp_path / "vault"),
                        "alexandria_root": "Alexandria",
                        "managed_markdown_count": 1,
                        "representative_path": str(
                            tmp_path / "vault" / "Alexandria" / "note.md"
                        ),
                        "representative_sha256": None,
                        "disk_free_bytes": None,
                    },
                    "diagnosis": ["test parent"],
                    "quarantine_artifacts": [],
                    "planned_steps": [
                        {
                            "code": "snapshot_sources",
                            "title": "Snapshot source vault metadata",
                            "mutates_state": False,
                        }
                    ],
                    "step_results": [
                        {
                            "code": "snapshot_sources",
                            "status": "SUCCEEDED",
                            "attempts": 1,
                            "started_at": "2026-07-16T12:00:00+00:00",
                            "finished_at": "2026-07-16T12:00:01+00:00",
                            "input_hash": snapshot_input_hash,
                            "result": {"managed_markdown_count": 1},
                        }
                    ],
                    "rebuild_results": {},
                    "verification_results": {},
                    "error_code": "READINESS_VERIFICATION_FAILED",
                    "error_summary": "test parent failed after snapshot",
                    "next_actions": ["retry_recovery_run"],
                }
            )
        )
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        service = RecoveryRunService(
            database=database,
            context_service=_FakeContextService(),
            obsidian_service=_FakeObsidianService(tmp_path / "vault"),
        )

        retry = await service.retry(
            parent_run_id,
            RecoveryPlanRequest(
                trigger="retry",
                actor="pytest",
                idempotency_key="retry-skip-key",
            ),
        )
        assert retry is not None
        first_step = retry.step_results[0]
        return (
            first_step.code,
            first_step.status,
            first_step.attempts,
            first_step.result,
        )

    code, status, attempts, result = anyio.run(scenario)

    assert {
        "code": code,
        "status": status.value,
        "attempts": attempts,
        "skipped_from_parent_run_id": result.get("skipped_from_parent_run_id"),
    } == {
        "code": "snapshot_sources",
        "status": "SKIPPED",
        "attempts": 0,
        "skipped_from_parent_run_id": "parent-with-snapshot",
    }


def test_recovery_run_retry_returns_none_for_unknown_parent(tmp_path: Path) -> None:
    """Retry should fail closed when the parent run manifest is unknown."""

    async def scenario() -> bool:
        database = Database(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'runtime.db'}",
            create_schema=True,
        )
        service = RecoveryRunService(
            database=database,
            context_service=_FakeContextService(),
            obsidian_service=_FakeObsidianService(tmp_path / "vault"),
        )

        retry = await service.retry(
            "missing-run",
            RecoveryPlanRequest(actor="pytest", idempotency_key="missing-retry-key"),
        )
        return retry is None

    assert anyio.run(scenario) is True


def test_recovery_run_rejects_new_start_when_active_lock_exists(
    tmp_path: Path,
) -> None:
    """Different recovery requests should fail closed while a run is active."""

    async def scenario() -> tuple[str, str]:
        database_path, _note, _note_body = _seed_corrupt_runtime(tmp_path)
        recovery_dir = tmp_path / ".alexandria-recovery"
        recovery_dir.mkdir()
        (recovery_dir / "active-run.json").write_text(
            '{"run_id":"existing-run","idempotency_key":"existing-key"}',
            encoding="utf-8",
        )
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        service = RecoveryRunService(
            database=database,
            context_service=_FakeContextService(),
            obsidian_service=_FakeObsidianService(tmp_path / "vault"),
        )

        try:
            await service.start(
                RecoveryPlanRequest(
                    trigger="manual",
                    actor="pytest",
                    idempotency_key="new-key",
                )
            )
        except RecoveryInProgressError as exc:
            return exc.run_id, exc.idempotency_key
        raise AssertionError("expected RecoveryInProgressError")

    run_id, idempotency_key = anyio.run(scenario)

    assert run_id == "existing-run"
    assert idempotency_key == "existing-key"


def test_recovery_run_rejects_new_start_when_active_lock_is_unreadable(
    tmp_path: Path,
) -> None:
    """Unreadable restart state should fail closed instead of starting mutation."""

    async def scenario() -> tuple[str, str | None, bytes]:
        database_path, _note, _note_body = _seed_corrupt_runtime(tmp_path)
        original_database_bytes = database_path.read_bytes()
        recovery_dir = tmp_path / ".alexandria-recovery"
        recovery_dir.mkdir()
        (recovery_dir / "active-run.json").write_text(
            "{not-json",
            encoding="utf-8",
        )
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        service = RecoveryRunService(
            database=database,
            context_service=_FakeContextService(),
            obsidian_service=_FakeObsidianService(tmp_path / "vault"),
        )

        try:
            await service.start(
                RecoveryPlanRequest(
                    trigger="manual",
                    actor="pytest",
                    idempotency_key="new-key-after-corrupt-lock",
                )
            )
        except RecoveryInProgressError as exc:
            return exc.run_id, exc.idempotency_key, database_path.read_bytes()
        raise AssertionError("expected RecoveryInProgressError")

    run_id, idempotency_key, database_after = anyio.run(scenario)

    assert run_id == "unreadable-active-recovery-lock"
    assert idempotency_key is None
    assert database_after == b"not a sqlite database"


def test_recovery_quarantine_inventory_lists_persisted_artifacts(
    tmp_path: Path,
) -> None:
    """Quarantine inventory should report stored artifacts without deleting them."""

    async def scenario() -> tuple[int, str, bool, int | None]:
        database_path, _note, _note_body = _seed_corrupt_runtime(tmp_path)
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        service = RecoveryRunService(
            database=database,
            context_service=_FakeContextService(),
            obsidian_service=_FakeObsidianService(tmp_path / "vault"),
        )
        run = await service.start(
            RecoveryPlanRequest(
                trigger="manual",
                actor="pytest",
                idempotency_key="inventory-key",
            )
        )
        items = await service.quarantine_inventory()

        return len(items), items[0].run_id, items[0].exists, items[0].size_bytes

    total, run_id, exists, size_bytes = anyio.run(scenario)

    assert total == 3
    assert run_id
    assert exists is True
    assert size_bytes is not None


def test_recovery_quarantine_inventory_is_empty_without_recovery_dir(
    tmp_path: Path,
) -> None:
    """Quarantine inventory should be empty when no recovery manifests exist."""

    async def scenario() -> int:
        database = Database(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'runtime.db'}",
            create_schema=True,
        )
        service = RecoveryRunService(
            database=database,
            context_service=_FakeContextService(),
            obsidian_service=_FakeObsidianService(tmp_path / "vault"),
        )
        items = await service.quarantine_inventory()
        return len(items)

    assert anyio.run(scenario) == 0
