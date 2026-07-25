"""Mutation operations executed by an operational recovery run."""

from __future__ import annotations

from app.operations.application.recovery_run_contracts import (
    ContextRecoveryService,
    ObsidianRecoveryService,
)
from app.shared.infrastructure.database import Database
from app.shared.types.extra_types import JSONObject


class RecoveryRunMutationOperations:
    """Execute destructive and rebuild steps through explicit service boundaries."""

    def __init__(
        self,
        *,
        database: Database,
        context_service: ContextRecoveryService,
        obsidian_service: ObsidianRecoveryService,
    ) -> None:
        """Initialize recovery mutation dependencies.

        Args:
            database: Shared database coordinator.
            context_service: Context embedding recovery boundary.
            obsidian_service: Obsidian index recovery boundary.
        """
        self._database = database
        self._context_service = context_service
        self._obsidian_service = obsidian_service

    async def dispose_connections(self) -> JSONObject:
        await self._database.engine.dispose()
        return {"disposed": True}

    async def rebuild_database(self) -> JSONObject:
        await self._database.initialize()
        return {"initialized": True}

    async def reindex_vault(self) -> JSONObject:
        result = await self._obsidian_service.reindex()
        return {
            "files_seen": result.files_seen,
            "files_indexed": result.files_indexed,
            "files_skipped": result.files_skipped,
            "stale_marked": result.stale_marked,
            "errors": list(result.errors),
        }

    async def reindex_embeddings(self) -> JSONObject:
        result = await self._context_service.reindex_embeddings(limit=1000, force=True)
        return {
            "scanned": result.scanned,
            "updated": result.updated,
            "skipped": result.skipped,
            "warnings": list(result.warnings),
        }
