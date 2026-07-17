"""Operational readiness router contracts."""

from __future__ import annotations

from pathlib import Path

import anyio
from app.memory.domain.entities.context_read_models import (
    ContextEmbeddingSourceStatus,
    RagDependencyHealth,
)
from app.memory.domain.event_enum.context_enums import RagHealthState, RagStrategy
from app.obsidian.domain.entities.obsidian_note import ObsidianVaultStatus
from app.operations.interface.routers.operational_readiness_router import (
    operational_readiness,
)
from app.shared.infrastructure.database import Database


class _FakeContextService:
    async def rag_health_with_index_status(self) -> RagDependencyHealth:
        return RagDependencyHealth(
            fts=RagHealthState.HEALTHY,
            vector=RagHealthState.HEALTHY,
            embedding=RagHealthState.REINDEX_REQUIRED,
            default_strategy=RagStrategy.FTS_ONLY,
            model_name="test-model",
            dimensions=3,
            fingerprint={"provider": "test"},
            warnings=["embedding mismatch"],
            source_statuses=[
                ContextEmbeddingSourceStatus(
                    source_name="obsidian_vault",
                    status=RagHealthState.REINDEX_REQUIRED,
                    total_rows=459,
                    current_rows=0,
                    stale_rows=459,
                    missing_rows=459,
                    current_fingerprint={"provider": "test"},
                    stored_fingerprints=[],
                )
            ],
        )


class _FakeObsidianService:
    def __init__(self, tmp_path: Path) -> None:
        self._tmp_path = tmp_path

    async def status(self) -> ObsidianVaultStatus:
        vault = self._tmp_path / "vault"
        root = vault / "Alexandria"
        root.mkdir(parents=True)
        return ObsidianVaultStatus(
            vault_path=str(vault),
            alexandria_root="Alexandria",
            vault_exists=True,
            alexandria_root_exists=True,
            indexed_notes=3,
            stale_notes=0,
            error_notes=0,
        )


def test_operational_readiness_route_returns_snapshot_payload(tmp_path: Path) -> None:
    """GET handler should expose the read-only snapshot response contract."""

    async def scenario() -> dict[str, object]:
        database = Database(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'route.db'}",
            create_schema=True,
        )
        await database.initialize()
        try:
            response = await operational_readiness(
                database=database,
                context_service=_FakeContextService(),
                obsidian_service=_FakeObsidianService(tmp_path),
            )
            return response.model_dump(mode="json")
        finally:
            await database.shutdown()

    payload = anyio.run(scenario)

    assert payload["status"] == "DEGRADED_FTS_ONLY"
    assert payload["ready"] is False
    assert payload["database"] == {
        "reachable": True,
        "integrity": "HEALTHY",
        "schema_version": "unknown",
        "corruption_detected": False,
    }
    assert payload["vault"]["indexed_notes"] == 3
    assert payload["rag"]["effective_strategy"] == "FTS_ONLY"
    assert payload["rag"]["source_statuses"] == [
        {
            "source_name": "obsidian_vault",
            "status": "REINDEX_REQUIRED",
            "total_rows": 459,
            "current_rows": 0,
            "stale_rows": 459,
            "missing_rows": 459,
            "current_fingerprint": {"provider": "test"},
            "stored_fingerprints": [],
        }
    ]
    assert payload["active_recovery_run_id"] is None
    assert payload["last_successful_recovery_run_id"] is None
    assert payload["warnings"] == ["rag_embedding_reindex_required"]
    assert payload["next_actions"] == ["reindex_embeddings"]
