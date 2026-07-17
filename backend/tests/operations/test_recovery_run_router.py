"""Recovery run router contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import anyio
import pytest
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
from app.operations.interface.routers.recovery_run_router import (
    get_recovery_run,
    recovery_quarantine,
    recovery_run,
    retry_recovery_run,
)
from app.operations.interface.schemas.operations.recovery_run_schema import (
    RecoveryRunRequestSchema,
    RecoveryRunRetryRequestSchema,
)
from app.shared.infrastructure.database import Database
from fastapi import HTTPException

_ORM_MODELS_LOADED = (
    _agent_models,
    _context_models,
    _librarian_provider_models,
    _obsidian_index_models,
    _skill_acquisition_job_models,
)


class _FakeContextService:
    async def rag_health_with_index_status(self) -> RagDependencyHealth:
        return RagDependencyHealth(
            fts=RagHealthState.HEALTHY,
            vector=RagHealthState.HEALTHY,
            embedding=RagHealthState.HEALTHY,
            default_strategy=RagStrategy.HYBRID,
            model_name="test-model",
            dimensions=3,
            fingerprint={"provider": "test"},
            warnings=[],
        )

    async def reindex_embeddings(
        self, limit: int = 100, *, force: bool = False
    ) -> ContextReindexResult:
        return ContextReindexResult(scanned=1, updated=1, skipped=0, warnings=[])


class _FakeObsidianService:
    def __init__(self, vault: Path) -> None:
        self._vault = vault

    async def status(self) -> ObsidianVaultStatus:
        return ObsidianVaultStatus(
            vault_path=str(self._vault),
            alexandria_root="Alexandria",
            vault_exists=True,
            alexandria_root_exists=True,
            indexed_notes=1,
            stale_notes=0,
            error_notes=0,
        )

    async def reindex(self) -> ObsidianReindexResult:
        return ObsidianReindexResult(
            files_seen=1,
            files_indexed=1,
            files_skipped=0,
            stale_marked=0,
            errors=[],
        )

    async def search(self, query, *, refresh: bool = True):  # type: ignore[no-untyped-def]
        _ = query
        _ = refresh
        return [
            ObsidianSearchHit(
                note=self._representative_note(),
                excerpt="운영 안정성 자동 복구 루프",
                score=1.0,
            )
        ]

    async def read_note(self, note_id: str) -> ObsidianNote:
        _ = note_id
        return self._representative_note()

    async def read_note_by_path(self, relative_path: str) -> ObsidianNote:
        _ = relative_path
        return self._representative_note()

    def _representative_note(self) -> ObsidianNote:
        return ObsidianNote(
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


def test_recovery_run_route_returns_completed_run_payload(tmp_path: Path) -> None:
    """POST handler should expose recovery run execution response."""

    async def scenario() -> dict[str, object]:
        database_path = tmp_path / "corrupt.db"
        database_path.write_bytes(b"not a sqlite database")
        note = tmp_path / "vault" / "Alexandria" / "note.md"
        note.parent.mkdir(parents=True)
        note.write_text("# Note\n", encoding="utf-8")
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        response = await recovery_run(
            request=RecoveryRunRequestSchema(idempotency_key="route-run-key"),
            database=database,
            context_service=_FakeContextService(),
            obsidian_service=_FakeObsidianService(tmp_path / "vault"),
        )
        return response.model_dump(mode="json")

    payload = anyio.run(scenario)

    assert payload["status"] == "COMPLETED"
    assert payload["idempotency_key"] == "route-run-key"
    assert payload["error_code"] is None
    assert payload["verification_results"]["ready"] is True
    assert payload["step_results"][-1]["code"] == "verify_readiness"
    assert all(len(step["input_hash"]) == 64 for step in payload["step_results"])


def test_recovery_run_route_exposes_source_preservation_evidence(
    tmp_path: Path,
) -> None:
    """POST response should expose full Markdown manifest preservation evidence."""

    async def scenario() -> dict[str, object]:
        database_path = tmp_path / "corrupt.db"
        database_path.write_bytes(b"not a sqlite database")
        vault = tmp_path / "vault"
        note_bodies = {
            "Alexandria/Contexts/Projects/project-a.md": b"# Project A\n",
            "Alexandria/Skills/Drafts/http-skill.md": b"# HTTP Skill\n",
        }
        for relative_path, body in note_bodies.items():
            note_path = vault / relative_path
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_bytes(body)
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        response = await recovery_run(
            request=RecoveryRunRequestSchema(
                idempotency_key="route-source-preservation-key"
            ),
            database=database,
            context_service=_FakeContextService(),
            obsidian_service=_FakeObsidianService(vault),
        )
        return response.model_dump(mode="json")

    payload = anyio.run(scenario)

    expected_manifest = {
        "Alexandria/Contexts/Projects/project-a.md": sha256(
            b"# Project A\n"
        ).hexdigest(),
        "Alexandria/Skills/Drafts/http-skill.md": sha256(b"# HTTP Skill\n").hexdigest(),
    }
    assert payload["status"] == "COMPLETED"
    assert payload["source_snapshot"]["markdown_manifest"] == expected_manifest
    assert payload["verification_results"]["source_preservation"] == {
        "preserved": True,
        "managed_markdown_count": 2,
        "removed_count": 0,
        "changed_count": 0,
        "added_count": 0,
        "removed_paths": [],
        "changed_paths": [],
        "added_paths": [],
    }


def test_get_recovery_run_route_returns_persisted_manifest(tmp_path: Path) -> None:
    """GET handler should return a previously persisted recovery run."""

    async def scenario() -> tuple[str, str, str]:
        database_path = tmp_path / "corrupt.db"
        database_path.write_bytes(b"not a sqlite database")
        note = tmp_path / "vault" / "Alexandria" / "note.md"
        note.parent.mkdir(parents=True)
        note.write_text("# Note\n", encoding="utf-8")
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        context_service = _FakeContextService()
        obsidian_service = _FakeObsidianService(tmp_path / "vault")
        created = await recovery_run(
            request=RecoveryRunRequestSchema(idempotency_key="route-get-key"),
            database=database,
            context_service=context_service,
            obsidian_service=obsidian_service,
        )
        loaded = await get_recovery_run(
            run_id=created.id,
            database=database,
            context_service=context_service,
            obsidian_service=obsidian_service,
        )
        return created.id, loaded.id, str(loaded.status)

    created_id, loaded_id, loaded_status = anyio.run(scenario)

    assert loaded_id == created_id
    assert loaded_status == "COMPLETED"


def test_get_recovery_run_route_restores_interrupted_active_lock_after_restart(
    tmp_path: Path,
) -> None:
    """GET handler should convert a stale active lock into a blocked manifest."""

    async def scenario() -> tuple[dict[str, object], bool, bool]:
        database_path = tmp_path / "runtime.db"
        vault_note = tmp_path / "vault" / "Alexandria" / "note.md"
        vault_note.parent.mkdir(parents=True)
        vault_note.write_text("# Note\n", encoding="utf-8")
        recovery_dir = tmp_path / ".alexandria-recovery"
        recovery_dir.mkdir()
        active_lock_path = recovery_dir / "active-run.json"
        active_lock_path.write_text(
            (
                '{"run_id":"interrupted-route-run",'
                '"idempotency_key":"interrupted-route-key",'
                '"trigger":"manual","actor":"pytest",'
                '"current_step":"reindex_vault",'
                '"started_at":"2026-07-16T12:00:00+00:00"}'
            ),
            encoding="utf-8",
        )
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )

        response = await get_recovery_run(
            run_id="interrupted-route-run",
            database=database,
            context_service=_FakeContextService(),
            obsidian_service=_FakeObsidianService(tmp_path / "vault"),
        )
        payload = response.model_dump(mode="json")
        return payload, active_lock_path.exists(), Path(response.manifest_path).exists()

    payload, active_lock_exists, manifest_exists = anyio.run(scenario)

    expected = {
        "id": "interrupted-route-run",
        "status": "BLOCKED",
        "current_step": "reindex_vault",
        "error_code": "RECOVERY_INTERRUPTED_AFTER_RESTART",
        "next_actions": ["retry_recovery_run", "inspect_recovery_run"],
    }
    assert {key: payload[key] for key in expected} == expected
    assert active_lock_exists is False
    assert manifest_exists is True


def test_retry_recovery_run_route_returns_child_run(tmp_path: Path) -> None:
    """POST retry handler should link the new run to the parent manifest."""

    async def scenario() -> dict[str, object]:
        database_path = tmp_path / "corrupt.db"
        database_path.write_bytes(b"not a sqlite database")
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        context_service = _FakeContextService()
        obsidian_service = _FakeObsidianService(tmp_path / "missing-vault")
        parent = await recovery_run(
            request=RecoveryRunRequestSchema(idempotency_key="route-blocked-parent"),
            database=database,
            context_service=context_service,
            obsidian_service=obsidian_service,
        )
        note = tmp_path / "missing-vault" / "Alexandria" / "note.md"
        note.parent.mkdir(parents=True)
        note.write_text("# Note\n", encoding="utf-8")

        response = await retry_recovery_run(
            run_id=parent.id,
            request=RecoveryRunRetryRequestSchema(idempotency_key="route-retry-key"),
            database=database,
            context_service=context_service,
            obsidian_service=obsidian_service,
        )
        return response.model_dump(mode="json")

    payload = anyio.run(scenario)

    assert payload["status"] == "COMPLETED"
    assert payload["parent_run_id"]
    assert payload["idempotency_key"] == "route-retry-key"
    assert payload["trigger"] == "retry"


def test_retry_recovery_run_route_returns_404_for_unknown_parent(
    tmp_path: Path,
) -> None:
    """POST retry handler should expose unknown parent as 404."""

    async def scenario() -> tuple[int, dict[str, object]]:
        database = Database(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'runtime.db'}",
            create_schema=True,
        )
        with pytest.raises(HTTPException) as raised:
            await retry_recovery_run(
                run_id="missing-run",
                request=RecoveryRunRetryRequestSchema(idempotency_key="missing-retry"),
                database=database,
                context_service=_FakeContextService(),
                obsidian_service=_FakeObsidianService(tmp_path / "vault"),
            )
        detail = raised.value.detail
        assert isinstance(detail, dict)
        return raised.value.status_code, detail

    status_code, detail = anyio.run(scenario)

    assert status_code == 404
    assert detail == {"code": "RECOVERY_RUN_NOT_FOUND", "run_id": "missing-run"}


def test_recovery_run_route_returns_409_when_recovery_in_progress(
    tmp_path: Path,
) -> None:
    """POST handler should surface active recovery lock as 409."""

    async def scenario() -> tuple[int, dict[str, object]]:
        database_path = tmp_path / "corrupt.db"
        database_path.write_bytes(b"not a sqlite database")
        note = tmp_path / "vault" / "Alexandria" / "note.md"
        note.parent.mkdir(parents=True)
        note.write_text("# Note\n", encoding="utf-8")
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
        with pytest.raises(HTTPException) as raised:
            await recovery_run(
                request=RecoveryRunRequestSchema(idempotency_key="new-key"),
                database=database,
                context_service=_FakeContextService(),
                obsidian_service=_FakeObsidianService(tmp_path / "vault"),
            )
        detail = raised.value.detail
        assert isinstance(detail, dict)
        return raised.value.status_code, detail

    status_code, detail = anyio.run(scenario)

    assert status_code == 409
    assert detail == {
        "code": "RECOVERY_IN_PROGRESS",
        "active_recovery_run_id": "existing-run",
        "idempotency_key": "existing-key",
    }


def test_recovery_run_route_returns_409_when_active_lock_is_unreadable(
    tmp_path: Path,
) -> None:
    """POST handler should fail closed when restart state cannot be parsed."""

    async def scenario() -> tuple[int, dict[str, object], bytes]:
        database_path = tmp_path / "corrupt.db"
        database_bytes = b"not a sqlite database"
        database_path.write_bytes(database_bytes)
        note = tmp_path / "vault" / "Alexandria" / "note.md"
        note.parent.mkdir(parents=True)
        note.write_text("# Note\n", encoding="utf-8")
        recovery_dir = tmp_path / ".alexandria-recovery"
        recovery_dir.mkdir()
        (recovery_dir / "active-run.json").write_text("{not-json", encoding="utf-8")
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        with pytest.raises(HTTPException) as raised:
            await recovery_run(
                request=RecoveryRunRequestSchema(idempotency_key="new-key"),
                database=database,
                context_service=_FakeContextService(),
                obsidian_service=_FakeObsidianService(tmp_path / "vault"),
            )
        detail = raised.value.detail
        assert isinstance(detail, dict)
        return raised.value.status_code, detail, database_path.read_bytes()

    status_code, detail, database_after = anyio.run(scenario)

    assert status_code == 409
    assert detail == {
        "code": "RECOVERY_IN_PROGRESS",
        "active_recovery_run_id": "unreadable-active-recovery-lock",
        "idempotency_key": None,
    }
    assert database_after == b"not a sqlite database"


def test_recovery_quarantine_route_returns_inventory(tmp_path: Path) -> None:
    """GET quarantine handler should expose persisted artifact inventory."""

    async def scenario() -> dict[str, object]:
        database_path = tmp_path / "corrupt.db"
        database_path.write_bytes(b"not a sqlite database")
        note = tmp_path / "vault" / "Alexandria" / "note.md"
        note.parent.mkdir(parents=True)
        note.write_text("# Note\n", encoding="utf-8")
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        context_service = _FakeContextService()
        obsidian_service = _FakeObsidianService(tmp_path / "vault")
        await recovery_run(
            request=RecoveryRunRequestSchema(idempotency_key="route-inventory-key"),
            database=database,
            context_service=context_service,
            obsidian_service=obsidian_service,
        )
        response = await recovery_quarantine(
            database=database,
            context_service=context_service,
            obsidian_service=obsidian_service,
        )
        return response.model_dump(mode="json")

    payload = anyio.run(scenario)

    assert payload["total"] == 3
    assert payload["items"][0]["run_id"]
    assert payload["items"][0]["exists"] is True
