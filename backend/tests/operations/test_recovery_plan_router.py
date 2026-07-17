"""Recovery plan router contracts."""

from __future__ import annotations

from pathlib import Path

import anyio
from app.memory.domain.entities.context_read_models import RagDependencyHealth
from app.memory.domain.event_enum.context_enums import RagHealthState, RagStrategy
from app.obsidian.domain.entities.obsidian_note import ObsidianVaultStatus
from app.operations.interface.routers.recovery_plan_router import recovery_plan
from app.operations.interface.schemas.operations.recovery_plan_schema import (
    RecoveryPlanRequestSchema,
)
from app.shared.infrastructure.database import Database


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


def test_recovery_plan_route_returns_read_only_plan_payload(tmp_path: Path) -> None:
    """POST handler should expose recovery dry-run plan contract."""

    async def scenario() -> dict[str, object]:
        database_path = tmp_path / "corrupt.db"
        database_path.write_bytes(b"not a sqlite database")
        note = tmp_path / "vault" / "Alexandria" / "note.md"
        note.parent.mkdir(parents=True)
        note.write_text("# Note\n", encoding="utf-8")
        database = Database(database_url=f"sqlite+aiosqlite:///{database_path}")
        response = await recovery_plan(
            request=RecoveryPlanRequestSchema(idempotency_key="route-key"),
            database=database,
            context_service=_FakeContextService(),
            obsidian_service=_FakeObsidianService(tmp_path / "vault"),
        )
        return response.model_dump(mode="json")

    payload = anyio.run(scenario)

    assert payload["status"] == "RECOVERY_REQUIRED"
    assert payload["dry_run"] is True
    assert payload["deletion_performed"] is False
    assert payload["automatic_execution_allowed"] is True
    assert payload["idempotency_key"] == "route-key"
    assert payload["diagnosis"] == ["SQLITE_CORRUPTION_DETECTED"]
    assert payload["quarantine_artifacts"][0]["source_path"] == str(
        tmp_path / "corrupt.db"
    )
    assert payload["steps"][0]["code"] == "snapshot_sources"
