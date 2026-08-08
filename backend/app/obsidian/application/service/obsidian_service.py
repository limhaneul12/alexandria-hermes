"""Application service for Obsidian-backed Alexandria notes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

from app.obsidian.application.librarian.obsidian_librarian_delegation import (
    ObsidianLibrarianDelegateService,
)
from app.obsidian.application.service.obsidian_context_lifecycle_service import (
    ObsidianContextLifecycleService,
)
from app.obsidian.application.service.obsidian_index_error_repair_service import (
    ObsidianIndexErrorRepairService,
)
from app.obsidian.application.service.obsidian_legacy_metadata_repair_service import (
    ObsidianLegacyMetadataRepairService,
)
from app.obsidian.application.service.obsidian_librarian_conversation_service import (
    ObsidianLibrarianConversationService,
)
from app.obsidian.application.service.obsidian_librarian_review_service import (
    ObsidianLibrarianReviewService,
)
from app.obsidian.application.service.obsidian_note_service import (
    ObsidianNoteService,
)
from app.obsidian.application.service.obsidian_vault_inventory_service import (
    ObsidianVaultInventoryService,
)
from app.obsidian.application.service.obsidian_vault_lifecycle_service import (
    ObsidianVaultLifecycleService,
)
from app.obsidian.application.service.obsidian_vault_move_service import (
    ObsidianVaultMoveService,
)
from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianLibrarianAsk,
    ObsidianLibrarianReviewApplyRequest,
    ObsidianLibrarianReviewQueueRequest,
    ObsidianSaveNote,
    ObsidianSearchQuery,
    ObsidianVaultInventoryRequest,
    ObsidianVaultMoveApplyRequest,
    ObsidianVaultMovePlanRequest,
    ObsidianVaultSettingsUpdate,
    ObsidianWriteNote,
)
from app.obsidian.domain.entities.obsidian_index_error_repair import (
    ObsidianIndexErrorRepairPlan,
    ObsidianIndexErrorRepairReport,
)
from app.obsidian.domain.entities.obsidian_legacy_metadata_repair import (
    ObsidianLegacyMetadataRepairPlan,
    ObsidianLegacyMetadataRepairReport,
)
from app.obsidian.domain.entities.obsidian_note import (
    ObsidianLibrarianReviewQueueItem,
    ObsidianNote,
    ObsidianNoteWriteResult,
    ObsidianReindexResult,
    ObsidianSearchHit,
    ObsidianVaultInventoryItem,
    ObsidianVaultLocation,
    ObsidianVaultMovePlan,
    ObsidianVaultMoveReport,
    ObsidianVaultStatus,
)
from app.obsidian.domain.repositories.obsidian_repository import (
    IObsidianIndexRepository,
)
from app.obsidian.infrastructure.obsidian_vault_config_store import (
    ObsidianVaultConfigStore,
)
from app.shared.application.index_maintenance_coordinator import (
    IndexMaintenanceCoordinator,
)
from app.shared.exceptions.obsidian_exceptions import (
    ObsidianValidationError,
)
from app.shared.types.extra_types import JSONObject


class ObsidianService:
    """Expose the stable Obsidian application facade.

    Focused inventory and vault-move responsibilities are delegated to
    collaborators while this facade preserves the existing router contract.
    """

    def __init__(
        self,
        *,
        repository: IObsidianIndexRepository,
        vault_path: str | None = None,
        alexandria_root: str = "Alexandria",
        vault_config_store: ObsidianVaultConfigStore | None = None,
        delegate_service: ObsidianLibrarianDelegateService | None = None,
        context_reindex_hook: Callable[[], Awaitable[None]] | None = None,
        index_maintenance_coordinator: IndexMaintenanceCoordinator | None = None,
    ) -> None:
        """Initialize service dependencies.

        Args:
            repository: Rebuildable PostgreSQL index repository.
            vault_path: Obsidian vault root.
            alexandria_root: Managed folder inside the vault.
            vault_config_store: Optional runtime vault override store.
            delegate_service: Optional provider-backed librarian delegate service.
        """
        self._repository = repository
        if vault_config_store is None:
            if vault_path is None:
                raise ObsidianValidationError("vault_path is required")
            vault_config_store = ObsidianVaultConfigStore(
                default_vault_path=vault_path,
                default_alexandria_root=alexandria_root,
                config_path=None,
            )
        self._vault_config_store = vault_config_store
        self._index_maintenance_coordinator = (
            index_maintenance_coordinator or IndexMaintenanceCoordinator()
        )
        self._context_lifecycle_service = ObsidianContextLifecycleService(
            repository=self._repository,
            vault_config_store=self._vault_config_store,
            read_note=self.read_note,
        )
        self._vault_lifecycle_service = ObsidianVaultLifecycleService(
            repository=self._repository,
            vault_config_store=self._vault_config_store,
            save_note=self.save_note,
            read_note_by_path=self.read_note_by_path,
            note_id_from_existing_file=self._note_id_from_existing_file,
            mark_context_superseded=self._delegate_mark_context_superseded,
            context_reindex_hook=context_reindex_hook,
            index_maintenance_coordinator=self._index_maintenance_coordinator,
        )
        self._index_error_repair_service = ObsidianIndexErrorRepairService(
            repository=self._repository,
            vault_config_store=self._vault_config_store,
            reindex=self.reindex,
            status=self.status,
        )
        self._legacy_metadata_repair_service = ObsidianLegacyMetadataRepairService(
            vault_config_store=self._vault_config_store,
            reindex=self.reindex,
        )
        self._note_service = ObsidianNoteService(
            repository=self._repository,
            vault_config_store=self._vault_config_store,
            reindex=self.reindex,
            mark_context_superseded=self._delegate_mark_context_superseded,
            index_maintenance_coordinator=self._index_maintenance_coordinator,
        )
        self._vault_inventory_service = ObsidianVaultInventoryService(
            vault_config_store=self._vault_config_store
        )
        self._vault_move_service = ObsidianVaultMoveService(
            vault_config_store=self._vault_config_store,
            reindex=self.reindex,
            search=self.search,
        )
        self._librarian_review_service = ObsidianLibrarianReviewService(
            vault_config_store=self._vault_config_store,
            inventory_service=self._vault_inventory_service,
            move_service=self._vault_move_service,
        )
        self._librarian_conversation_service = ObsidianLibrarianConversationService(
            vault_config_store=self._vault_config_store,
            delegate_service=delegate_service,
            read_note_by_path=self.read_note_by_path,
            save_note=self.save_note,
            search=self.search,
        )

    @property
    def _vault_path(self) -> Path:
        return self._vault_config_store.current().vault_path

    @property
    def _alexandria_root(self) -> str:
        return self._vault_config_store.current().alexandria_root

    def vault_location(self) -> ObsidianVaultLocation:
        """Return the canonical Vault path without reading the PostgreSQL index.

        Returns:
            Vault and managed-root location used by source-preserving backups.
        """
        config = self._vault_config_store.current()
        return ObsidianVaultLocation(
            vault_path=str(config.vault_path),
            alexandria_root=config.alexandria_root,
        )

    async def status(self) -> ObsidianVaultStatus:
        """Return local Obsidian vault and index status.

        Returns:
            Current vault and index status.
        """
        return await self._vault_lifecycle_service.status()

    async def configure_vault_settings(
        self,
        payload: ObsidianVaultSettingsUpdate,
    ) -> ObsidianVaultStatus:
        """Change the runtime Obsidian vault destination.

        Args:
            payload: Vault settings update request.

        Returns:
            Current vault and index status after applying settings.
        """
        return await self._vault_lifecycle_service.configure(payload)

    async def initialize_vault(self) -> ObsidianNote:
        """Create the managed folder layout and START_HERE note.

        Returns:
            The canonical START_HERE note.
        """
        return await self._vault_lifecycle_service.initialize()

    async def reindex(self) -> ObsidianReindexResult:
        """Scan managed Markdown notes and rebuild changed index rows.

        Returns:
            Reindex summary with counts and warnings.
        """
        return await self._vault_lifecycle_service.reindex()

    async def plan_index_error_repairs(self) -> ObsidianIndexErrorRepairPlan:
        """Build a non-mutating plan for known legacy index errors.

        Returns:
            Hash-locked repair plan.
        """
        return await self._index_error_repair_service.plan()

    async def apply_index_error_repairs(
        self,
        *,
        expected_plan_hash: str,
    ) -> ObsidianIndexErrorRepairReport:
        """Apply a hash-locked, backup-first legacy index repair plan.

        Args:
            expected_plan_hash: Plan hash accepted by the operator.

        Returns:
            Applied repair report.
        """
        return await self._index_error_repair_service.apply(
            expected_plan_hash=expected_plan_hash
        )

    async def plan_legacy_metadata_repairs(
        self,
    ) -> ObsidianLegacyMetadataRepairPlan:
        """Scan managed Markdown for repairable legacy metadata.

        Returns:
            Non-mutating metadata repair plan.
        """
        return await self._legacy_metadata_repair_service.plan()

    async def apply_legacy_metadata_repairs(
        self,
        *,
        expected_plan_hash: str,
    ) -> ObsidianLegacyMetadataRepairReport:
        """Apply an unchanged, backup-first legacy metadata repair plan.

        Args:
            expected_plan_hash: Hash of the inspected plan accepted for apply.

        Returns:
            Applied repair report with content-hash evidence.
        """
        return await self._legacy_metadata_repair_service.apply(
            expected_plan_hash=expected_plan_hash
        )

    async def inventory_vault(
        self,
        request: ObsidianVaultInventoryRequest,
    ) -> list[ObsidianVaultInventoryItem]:
        """Inventory managed Markdown notes under a vault-relative scope.

        Args:
            request: Inventory request with optional scope path.

        Returns:
            Managed note inventory items sorted by path.
        """
        return await self._vault_inventory_service.inventory(request)

    async def managed_markdown_paths(self) -> list[str]:
        """List every managed Markdown source regardless of index validity.

        Returns:
            Vault-relative managed Markdown paths.
        """
        return await self._vault_inventory_service.managed_markdown_paths()

    async def search_vault_paths(
        self,
        *,
        query: str,
        scope_path: str | None = None,
    ) -> list[ObsidianVaultInventoryItem]:
        """Search inventoried paths and note metadata without relying on FTS.

        Args:
            query: Keyword or path fragment to find.
            scope_path: Optional vault-relative scope.

        Returns:
            Matching managed note inventory items.
        """
        return await self._vault_inventory_service.search_paths(
            query=query,
            scope_path=scope_path,
        )

    async def librarian_review_queue(
        self,
        request: ObsidianLibrarianReviewQueueRequest,
    ) -> list[ObsidianLibrarianReviewQueueItem]:
        """List managed notes that need librarian curation.

        Args:
            request: Review queue scope, project, and limit contract.

        Returns:
            Prioritized librarian review candidates.
        """
        return await self._librarian_review_service.review_queue(request)

    async def plan_librarian_review_moves(
        self,
        request: ObsidianLibrarianReviewQueueRequest,
    ) -> ObsidianVaultMovePlan:
        """Build a dry-run move plan from librarian review candidates.

        Args:
            request: Review queue scope, project, and limit contract.

        Returns:
            Safety-validated move plan.
        """
        return await self._librarian_review_service.plan_moves(request)

    async def apply_librarian_review_moves(
        self,
        request: ObsidianLibrarianReviewApplyRequest,
    ) -> ObsidianVaultMoveReport:
        """Apply safe moves generated from librarian review candidates.

        Args:
            request: Review queue and report application contract.

        Returns:
            Applied move report and verification metadata.
        """
        return await self._librarian_review_service.apply_moves(request)

    async def plan_vault_moves(
        self,
        request: ObsidianVaultMovePlanRequest,
    ) -> ObsidianVaultMovePlan:
        """Build a dry-run move plan without mutating the vault.

        Args:
            request: Requested vault moves.

        Returns:
            Safety-validated move plan.
        """
        return await self._vault_move_service.plan(request)

    async def apply_vault_moves(
        self,
        request: ObsidianVaultMoveApplyRequest,
    ) -> ObsidianVaultMoveReport:
        """Safely apply a move plan, reindex, verify, and write reports.

        Args:
            request: Move application and verification contract.

        Returns:
            Applied move report and report paths.
        """
        return await self._vault_move_service.apply(request)

    async def search(
        self,
        query: ObsidianSearchQuery,
        *,
        refresh: bool = False,
    ) -> list[ObsidianSearchHit]:
        """Search Obsidian notes through the PostgreSQL index.

        Args:
            query: Search filters and query text.
            refresh: Whether to re-scan the vault before querying.

        Returns:
            Ranked search hits.
        """
        return await self._note_service.search(query, refresh=refresh)

    async def read_note(self, note_id: str) -> ObsidianNote:
        """Read one managed note by stable id.

        Args:
            note_id: Stable note id from frontmatter.

        Returns:
            Authoritative note loaded from Markdown.
        """
        return await self._note_service.read_note(note_id)

    async def read_note_by_path(self, relative_path: str) -> ObsidianNote:
        """Read one managed note by vault-relative path.

        Args:
            relative_path: Vault-relative Markdown path.

        Returns:
            Authoritative note loaded from Markdown.
        """
        return await self._note_service.read_note_by_path(relative_path)

    async def save_note(self, payload: ObsidianSaveNote) -> ObsidianNote:
        """Create or replace one Alexandria-managed Markdown note.

        Args:
            payload: Save request with body and metadata.

        Returns:
            Saved note loaded through the index.
        """
        return await self._note_service.save_note(payload)

    async def write_note(
        self,
        command: ObsidianWriteNote,
    ) -> ObsidianNoteWriteResult:
        """Execute explicit create, update, or upsert semantics.

        Args:
            command: Value supplied to write_note.

        Returns:
            Result produced by write_note.
        """
        return await self._note_service.write_note(command)

    async def archive_context(self, note_id: str) -> ObsidianNote:
        """Archive one canonical Context while preserving its Markdown content.

        Args:
            note_id: Canonical Obsidian note identifier.

        Returns:
            Reindexed archived Context note.
        """
        return await self._context_lifecycle_service.archive(note_id)

    async def supersede_context(
        self,
        note_id: str,
        replacement_note_id: str,
    ) -> tuple[ObsidianNote, ObsidianNote]:
        """Link an existing canonical Context to an existing replacement.

        Args:
            note_id: Canonical Context identifier to supersede.
            replacement_note_id: Canonical replacement Context identifier.

        Returns:
            Superseded and replacement canonical notes.
        """
        return await self._context_lifecycle_service.supersede(
            note_id,
            replacement_note_id,
        )

    async def _delegate_mark_context_superseded(
        self,
        *,
        superseded_context_id: str,
        replacement_context_id: str,
    ) -> None:
        await self._mark_context_superseded(
            superseded_context_id=superseded_context_id,
            replacement_context_id=replacement_context_id,
        )

    async def _mark_context_superseded(
        self,
        superseded_context_id: str,
        replacement_context_id: str,
    ) -> None:
        await self._context_lifecycle_service.mark_superseded(
            superseded_context_id=superseded_context_id,
            replacement_context_id=replacement_context_id,
        )

    async def apply_librarian_graph_links(
        self,
        *,
        active_note_path: str,
        response: JSONObject,
    ) -> ObsidianNote:
        """Apply approved librarian source refs to an active note.

        Args:
            active_note_path: Vault-relative note path approved for mutation.
            response: Librarian response containing source references.

        Returns:
            Updated active note.
        """
        return await self._librarian_conversation_service.apply_graph_links(
            active_note_path=active_note_path,
            response=response,
        )

    def _note_id_from_existing_file(self, path: Path) -> str | None:
        return self._note_service.note_id_from_existing_file(path)

    async def ask_librarian(self, payload: ObsidianLibrarianAsk) -> JSONObject:
        """Return an Obsidian-grounded librarian answer payload.

        Args:
            payload: Librarian question and optional active-note context.

        Returns:
            JSON-compatible answer, evidence, and transcript metadata.
        """
        return await self._librarian_conversation_service.ask(payload)
