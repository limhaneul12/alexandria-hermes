"""Application service for Obsidian-backed Alexandria notes."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from app.obsidian.application.obsidian_authoritative_read import (
    authoritative_note_from_path,
)
from app.obsidian.application.obsidian_frontmatter_redaction import (
    redacted_frontmatter,
)
from app.obsidian.application.obsidian_graph_relations import (
    add_or_update_alexandria_links_section,
)
from app.obsidian.application.obsidian_graph_writeback import graph_link_save_payload
from app.obsidian.application.obsidian_librarian_delegation import (
    ObsidianLibrarianDelegateService,
    apply_provider_delegate,
)
from app.obsidian.application.obsidian_librarian_retrieval import (
    librarian_excluded_types,
    librarian_query_text,
    librarian_query_variants,
    librarian_search_limit,
    librarian_type_filters,
)
from app.obsidian.application.obsidian_note_indexer import note_index_from_path
from app.obsidian.application.obsidian_note_templates import (
    LIBRARIAN_OPERATIONS_FOLDER,
    conversation_id,
    default_folders,
    default_note_path,
    frontmatter_for_save,
    librarian_answer,
    librarian_transcript_body,
    source_refs_for_librarian,
    start_here_body,
)
from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianLibrarianAsk,
    ObsidianSaveNote,
    ObsidianSearchQuery,
    ObsidianVaultInventoryRequest,
    ObsidianVaultMoveApplyRequest,
    ObsidianVaultMovePlanRequest,
    ObsidianVaultMoveRequest,
    ObsidianVaultSettingsUpdate,
)
from app.obsidian.domain.entities.obsidian_note import (
    ObsidianNote,
    ObsidianReindexResult,
    ObsidianSearchHit,
    ObsidianVaultInventoryItem,
    ObsidianVaultMoveApplied,
    ObsidianVaultMoveCandidate,
    ObsidianVaultMovePlan,
    ObsidianVaultMoveReport,
    ObsidianVaultMoveSkip,
    ObsidianVaultMoveVerification,
    ObsidianVaultStatus,
)
from app.obsidian.domain.event_enum.obsidian_enums import AlexandriaNoteType
from app.obsidian.domain.repositories.obsidian_repository import (
    IObsidianIndexRepository,
)
from app.obsidian.infrastructure.markdown.frontmatter import (
    frontmatter_text,
    parse_markdown_document,
    render_markdown_document,
)
from app.obsidian.infrastructure.markdown.paths import (
    NOTE_SUFFIX,
    resolve_note_path,
    safe_relative_path,
)
from app.obsidian.infrastructure.obsidian_vault_config_store import (
    ObsidianVaultConfig,
    ObsidianVaultConfigStore,
)
from app.shared.exceptions import ObsidianNotFoundError, ObsidianValidationError
from app.shared.infrastructure.identifiers import new_uuid
from app.shared.serialization.orjson_codec import dumps_pretty_json
from app.shared.types.extra_types import JSONObject
from app.shared.utils.secret_redaction import redact_secret_text

SELECTION_CONTEXT_MAX_CHARS = 4_000
NOTE_SUFFIX_GLOB = f"*{NOTE_SUFFIX}"


class ObsidianService:
    """Coordinate Obsidian vault IO and rebuildable SQLite indexing."""

    def __init__(
        self,
        *,
        repository: IObsidianIndexRepository,
        vault_path: str | None = None,
        alexandria_root: str = "Alexandria",
        vault_config_store: ObsidianVaultConfigStore | None = None,
        delegate_service: ObsidianLibrarianDelegateService | None = None,
    ) -> None:
        """Initialize service dependencies.

        Args:
            repository: Rebuildable SQLite index repository.
            vault_path: Obsidian vault root.
            alexandria_root: Managed folder inside the vault.
            vault_config_store: Optional runtime vault override store.
            delegate_service: Optional provider-backed librarian delegate service.
        """
        self._repository = repository
        self._delegate_service = delegate_service
        if vault_config_store is None:
            if vault_path is None:
                raise ObsidianValidationError("vault_path is required")
            vault_config_store = ObsidianVaultConfigStore(
                default_vault_path=vault_path,
                default_alexandria_root=alexandria_root,
                config_path=None,
            )
        self._vault_config_store = vault_config_store

    @property
    def _vault_path(self) -> Path:
        return self._vault_config_store.current().vault_path

    @property
    def _alexandria_root(self) -> str:
        return self._vault_config_store.current().alexandria_root

    async def status(self) -> ObsidianVaultStatus:
        """Return local Obsidian vault/index status.

        Returns:
            Current vault/index status.
        """
        indexed, stale, errors = await self._repository.count_by_status()
        root = self._root_path()
        return ObsidianVaultStatus(
            vault_path=str(self._vault_path),
            alexandria_root=self._alexandria_root,
            vault_exists=self._vault_path.exists(),
            alexandria_root_exists=root.exists(),
            indexed_notes=indexed,
            stale_notes=stale,
            error_notes=errors,
        )

    async def configure_vault_settings(
        self,
        payload: ObsidianVaultSettingsUpdate,
    ) -> ObsidianVaultStatus:
        """Change the runtime Obsidian vault destination.

        Args:
            payload: Vault settings update request.

        Returns:
            Current vault/index status after applying the settings.
        """
        config = self._vault_config_store.normalized(
            vault_path=payload.vault_path,
            alexandria_root=payload.alexandria_root,
        )
        if payload.initialize:
            self._ensure_vault_layout(config)
        self._vault_config_store.save(config)
        if payload.initialize:
            await self.initialize_vault()
        if payload.reindex:
            await self.reindex()
        return await self.status()

    async def initialize_vault(self) -> ObsidianNote:
        """Create the managed Obsidian folder layout and START_HERE note.

        Returns:
            The START_HERE note.
        """
        for folder in default_folders(self._alexandria_root):
            resolve_note_path(self._vault_path, folder).mkdir(
                parents=True, exist_ok=True
            )
        start_path = f"{self._alexandria_root}/START_HERE.md"
        absolute = resolve_note_path(self._vault_path, start_path)
        if not absolute.exists():
            note = await self.save_note(
                ObsidianSaveNote(
                    note_id="alexandria_start_here",
                    title="Alexandria START HERE",
                    body=start_here_body(),
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    relative_path=start_path,
                    tags=["alexandria", "start-here"],
                    status="active",
                    source="alexandria-hermes",
                    frontmatter={"kind": "project_context", "scope": "project"},
                )
            )
            return note
        result = await self.reindex()
        if result.files_indexed == 0:
            indexed = await self.read_note_by_path(start_path)
            return indexed
        indexed = await self.read_note_by_path(start_path)
        return indexed

    async def reindex(self) -> ObsidianReindexResult:
        """Scan managed Markdown notes and rebuild changed index rows.

        Returns:
            Reindex summary with counts and warnings.
        """
        root = self._root_path()
        if not root.exists():
            return ObsidianReindexResult(
                files_seen=0,
                files_indexed=0,
                files_skipped=0,
                stale_marked=await self._repository.mark_missing_stale(set()),
                errors=["Alexandria Obsidian root does not exist"],
            )
        files_seen = 0
        files_indexed = 0
        files_skipped = 0
        errors: list[str] = []
        seen_paths: set[str] = set()
        for path in sorted(root.rglob(f"*{NOTE_SUFFIX}")):
            files_seen += 1
            relative_path = str(path.relative_to(self._vault_path))
            seen_paths.add(relative_path)
            try:
                payload = note_index_from_path(
                    path,
                    relative_path,
                    alexandria_root=self._alexandria_root,
                )
                if payload is None:
                    files_skipped += 1
                    continue
                await self._repository.upsert_note(payload)
                files_indexed += 1
            except (OSError, ValueError) as exc:
                errors.append(f"{relative_path}: {exc}")
        stale_marked = await self._repository.mark_missing_stale(seen_paths)
        return ObsidianReindexResult(
            files_seen=files_seen,
            files_indexed=files_indexed,
            files_skipped=files_skipped,
            stale_marked=stale_marked,
            errors=errors,
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
        scope = self._scope_path(request.scope_path)
        if not scope.exists():
            return []
        note_paths = (
            [scope] if scope.is_file() else sorted(scope.rglob(NOTE_SUFFIX_GLOB))
        )
        items: list[ObsidianVaultInventoryItem] = []
        for path in note_paths:
            if not path.is_file() or path.suffix != NOTE_SUFFIX:
                continue
            relative_path = str(path.relative_to(self._vault_path))
            payload = note_index_from_path(
                path,
                relative_path,
                alexandria_root=self._alexandria_root,
            )
            if payload is None:
                continue
            items.append(
                ObsidianVaultInventoryItem(
                    note_id=payload.note_id,
                    relative_path=payload.relative_path,
                    alexandria_type=payload.alexandria_type,
                    title=payload.title,
                    status=payload.status,
                    tags=payload.tags,
                    project=payload.project,
                    size_bytes=payload.size_bytes,
                    modified_at=payload.modified_at,
                )
            )
        return items

    async def search_vault_paths(
        self,
        *,
        query: str,
        scope_path: str | None = None,
    ) -> list[ObsidianVaultInventoryItem]:
        """Search inventoried paths and note metadata without relying on FTS.

        Args:
            query: Keyword/path fragment to find.
            scope_path: Optional vault-relative scope.

        Returns:
            Matching inventory items.
        """
        needle = query.casefold().strip()
        if not needle:
            raise ObsidianValidationError("query is required")
        items = await self.inventory_vault(
            ObsidianVaultInventoryRequest(scope_path=scope_path)
        )
        return [item for item in items if _inventory_item_matches(item, needle)]

    async def plan_vault_moves(
        self,
        request: ObsidianVaultMovePlanRequest,
    ) -> ObsidianVaultMovePlan:
        """Build a dry-run move plan without mutating the vault.

        Args:
            request: Requested safe moves.

        Returns:
            Safety-validated move plan.
        """
        moves: list[ObsidianVaultMoveCandidate] = []
        skipped: list[ObsidianVaultMoveSkip] = []
        for move in request.moves:
            issue = self._move_safety_issue(move)
            if issue is not None:
                skipped.append(issue)
                continue
            moves.append(
                ObsidianVaultMoveCandidate(
                    source_path=move.source_path,
                    destination_path=move.destination_path,
                    reason=move.reason,
                )
            )
        status = "ready" if moves and not skipped else "blocked" if skipped else "empty"
        return ObsidianVaultMovePlan(
            status=status,
            hard_delete_performed=False,
            moves=moves,
            skipped=skipped,
            ambiguous=[],
        )

    async def apply_vault_moves(
        self,
        request: ObsidianVaultMoveApplyRequest,
    ) -> ObsidianVaultMoveReport:
        """Safely apply a move plan, reindex, verify, and write reports.

        Args:
            request: Move application request.

        Returns:
            Markdown/JSON report metadata.
        """
        plan = await self.plan_vault_moves(
            ObsidianVaultMovePlanRequest(moves=request.moves)
        )
        report_paths = self._vault_move_report_paths(request)
        self._ensure_vault_move_report_available(report_paths)
        moved: list[ObsidianVaultMoveApplied] = []
        skipped = list(plan.skipped)
        applicable_moves = self._applicable_vault_moves(plan.moves, skipped)
        source_roots: set[Path] = set()
        for move in applicable_moves:
            source = resolve_note_path(self._vault_path, move.source_path)
            destination = resolve_note_path(self._vault_path, move.destination_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            source_roots.add(source.parent)
            source.replace(destination)
            moved.append(
                ObsidianVaultMoveApplied(
                    source_path=move.source_path,
                    destination_path=move.destination_path,
                    reason=move.reason,
                )
            )
        reindex_status = "skipped"
        verification_hits = 0
        if request.reindex:
            result = await self.reindex()
            reindex_status = "succeeded" if not result.errors else "failed"
            if request.verification_query is not None:
                hits = await self.search(
                    ObsidianSearchQuery(query=request.verification_query, limit=10),
                    refresh=False,
                )
                verification_hits = len(hits)
        verification = ObsidianVaultMoveVerification(
            source_root_loose_notes_remaining=_loose_note_count(source_roots),
            reindex_status=reindex_status,
            verification_hits=verification_hits,
        )
        status = (
            "succeeded" if moved and not skipped else "partial" if moved else "failed"
        )
        report_markdown_path, report_json_path = self._write_vault_move_report(
            report_paths=report_paths,
            status=status,
            moved=moved,
            skipped=skipped,
            verification=verification,
        )
        return ObsidianVaultMoveReport(
            status=status,
            hard_delete_performed=False,
            moved=moved,
            skipped=skipped,
            ambiguous=list(plan.ambiguous),
            verification=verification,
            report_markdown_path=report_markdown_path,
            report_json_path=report_json_path,
        )

    async def search(
        self,
        query: ObsidianSearchQuery,
        *,
        refresh: bool = True,
    ) -> list[ObsidianSearchHit]:
        """Search Obsidian notes through the SQLite index.

        Args:
            query: Search filters and query text.
            refresh: Whether to re-scan the vault before querying.

        Returns:
            Ranked search hits.
        """
        if refresh:
            await self.reindex()
        return await self._repository.search(query)

    async def read_note(self, note_id: str) -> ObsidianNote:
        """Read one managed note by stable id and reload its Markdown body.

        Args:
            note_id: Stable note id from frontmatter.

        Returns:
            Authoritative note loaded from Markdown.
        """
        indexed = await self._repository.get_by_id(note_id)
        if indexed is None:
            await self.reindex()
            indexed = await self._repository.get_by_id(note_id)
        if indexed is None:
            raise ObsidianNotFoundError(f"Obsidian note not found: {note_id}")
        return authoritative_note_from_path(
            vault_path=self._vault_path,
            relative_path=indexed.relative_path,
            alexandria_root=self._alexandria_root,
            indexed=indexed,
        )

    async def read_note_by_path(self, relative_path: str) -> ObsidianNote:
        """Read one managed note by vault-relative path.

        Args:
            relative_path: Vault-relative Markdown path.

        Returns:
            Authoritative note loaded from Markdown.
        """
        safe_path = str(safe_relative_path(relative_path))
        indexed = await self._repository.get_by_path(safe_path)
        if indexed is None:
            await self.reindex()
            indexed = await self._repository.get_by_path(safe_path)
        if indexed is None:
            raise ObsidianNotFoundError(f"Obsidian note not found: {safe_path}")
        return authoritative_note_from_path(
            vault_path=self._vault_path,
            relative_path=safe_path,
            alexandria_root=self._alexandria_root,
            indexed=indexed,
        )

    async def save_note(self, payload: ObsidianSaveNote) -> ObsidianNote:
        """Create or replace one Alexandria-managed Markdown note.

        Args:
            payload: Save request with body and metadata.

        Returns:
            Saved note loaded through the index.
        """
        title = payload.title.strip()
        if not title:
            raise ObsidianValidationError("title is required")
        redaction = redact_secret_text(payload.body)
        if redaction.blocked:
            raise ObsidianValidationError("high-risk secret content cannot be saved")
        frontmatter_payload, frontmatter_warnings = redacted_frontmatter(
            payload.frontmatter
        )
        payload = replace(payload, frontmatter=frontmatter_payload)
        relative_path = payload.relative_path or default_note_path(
            root=self._alexandria_root,
            note_type=payload.alexandria_type,
            title=title,
        )
        safe_path = str(safe_relative_path(relative_path))
        absolute = resolve_note_path(self._vault_path, safe_path)
        indexed_note = await self._repository.get_by_path(safe_path)
        if (
            payload.note_id is not None
            and indexed_note is not None
            and indexed_note.note_id != payload.note_id
        ):
            raise ObsidianValidationError(
                f"Obsidian path is already indexed with a different id: {safe_path}"
            )
        note_id = (
            payload.note_id
            or (None if indexed_note is None else indexed_note.note_id)
            or self._note_id_from_existing_file(absolute)
            or new_uuid()
        )
        absolute.parent.mkdir(parents=True, exist_ok=True)
        frontmatter = frontmatter_for_save(
            payload,
            note_id=note_id,
            title=title,
            redaction_warnings=[*redaction.warnings, *frontmatter_warnings],
        )
        body = add_or_update_alexandria_links_section(
            redaction.redacted_content, frontmatter
        )
        document = render_markdown_document(frontmatter, body)
        temp_path = absolute.with_suffix(f"{NOTE_SUFFIX}.tmp")
        temp_path.write_text(document, encoding="utf-8")
        temp_path.replace(absolute)
        index_payload = note_index_from_path(
            absolute,
            safe_path,
            alexandria_root=self._alexandria_root,
        )
        if index_payload is None:
            raise ObsidianValidationError(
                "saved note is missing Alexandria frontmatter"
            )
        note = await self._repository.upsert_note(index_payload)
        return note

    async def apply_librarian_graph_links(
        self,
        *,
        active_note_path: str,
        response: JSONObject,
    ) -> ObsidianNote:
        """Apply approved librarian source refs to an active note and reindex it.

        Args:
            active_note_path: Vault-relative path of the note approved for mutation.
            response: Librarian answer payload containing source refs.

        Returns:
            Updated active note loaded from the rebuilt index.
        """
        note = await self.read_note_by_path(active_note_path)
        return await self.save_note(
            graph_link_save_payload(note=note, response=response)
        )

    def _note_id_from_existing_file(self, path: Path) -> str | None:
        if not path.exists():
            return None
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return None
        document = parse_markdown_document(text)
        return frontmatter_text(document.frontmatter, "id")

    async def ask_librarian(self, payload: ObsidianLibrarianAsk) -> JSONObject:
        """Return an Obsidian-grounded librarian answer payload.

        Args:
            payload: Librarian question and optional active-note context.

        Returns:
            JSON-compatible answer payload with source references.
        """
        if not payload.query.strip():
            raise ObsidianValidationError("query is required")
        active_note = await self._active_note(payload.active_note_path)
        selection_excerpt = _selection_excerpt(payload.selection)
        hits = await self._librarian_source_hits(payload)
        answer = librarian_answer(payload, hits, active_note)
        source_refs = source_refs_for_librarian(hits, active_note)
        input_context = _librarian_input_context(
            payload=payload,
            active_note=active_note,
            selection_excerpt=selection_excerpt,
            source_refs=source_refs,
        )
        response: JSONObject = {
            "answer_markdown": answer,
            "source_refs": source_refs,
            "input_context": input_context,
            "context_status": str(input_context["status"]),
            "action_preview": [
                "save_chat",
                "create_context_note",
                "create_skill_draft",
            ],
            "conversation_id": conversation_id(),
            "transcript_path": None,
            "delegate_status": _delegate_status(payload),
            "provider_id": payload.provider_id,
            "profile_id": payload.profile_id,
        }
        await apply_provider_delegate(
            payload=payload,
            response=response,
            delegate_service=self._delegate_service,
        )
        if payload.save_transcript:
            transcript = await self._save_librarian_chat(
                payload, str(response["answer_markdown"]), hits, response
            )
            response["transcript_path"] = transcript.relative_path
        return response

    async def _active_note(self, relative_path: str | None) -> ObsidianNote | None:
        if not relative_path:
            return None
        try:
            return await self.read_note_by_path(relative_path)
        except ObsidianNotFoundError as exc:
            raise ObsidianValidationError(
                f"active_note_read_failed: {relative_path}"
            ) from exc

    async def _save_librarian_chat(
        self,
        payload: ObsidianLibrarianAsk,
        answer: str,
        hits: list[ObsidianSearchHit],
        response: JSONObject,
    ) -> ObsidianNote:
        conversation_id = str(response["conversation_id"])
        body = librarian_transcript_body(payload, answer, hits)
        return await self.save_note(
            ObsidianSaveNote(
                title=f"Librarian Chat {conversation_id}",
                body=body,
                alexandria_type=AlexandriaNoteType.LIBRARIAN_CHAT,
                note_id=conversation_id,
                relative_path=(
                    f"{self._alexandria_root}/{LIBRARIAN_OPERATIONS_FOLDER}/"
                    f"Chats/{conversation_id}.md"
                ),
                tags=["librarian", "obsidian-chat"],
                project=payload.project,
                source="obsidian-plugin",
                frontmatter={
                    "conversation_id": conversation_id,
                    "active_note_path": payload.active_note_path,
                    "linked_note_ids": [hit.note.note_id for hit in hits],
                    "source_refs": [
                        {
                            "id": hit.note.note_id,
                            "path": hit.note.relative_path,
                            "relation": "cites",
                        }
                        for hit in hits
                    ],
                },
            )
        )

    async def _librarian_source_hits(
        self, payload: ObsidianLibrarianAsk
    ) -> list[ObsidianSearchHit]:
        query_text = librarian_query_text(payload)
        search_limit = librarian_search_limit(payload.max_source_refs)
        preferred_types = librarian_type_filters(payload.preferred_alexandria_types)
        excluded_types = librarian_excluded_types(preferred_types)
        hits_by_note_id: dict[str, ObsidianSearchHit] = {}
        for query_variant in librarian_query_variants(query_text):
            search_queries = _librarian_search_queries(
                query=query_variant,
                limit=search_limit,
                project=payload.project,
                preferred_types=preferred_types,
                excluded_types=excluded_types,
            )
            for search_query in search_queries:
                hits = await self.search(search_query)
                for hit in hits:
                    hits_by_note_id.setdefault(hit.note.note_id, hit)
                    if len(hits_by_note_id) >= payload.max_source_refs:
                        return list(hits_by_note_id.values())
        return list(hits_by_note_id.values())

    def _root_path(self) -> Path:
        return resolve_note_path(self._vault_path, self._alexandria_root)

    def _scope_path(self, scope_path: str | None) -> Path:
        scope = self._alexandria_root if scope_path is None else scope_path
        return resolve_note_path(self._vault_path, scope)

    def _move_safety_issue(
        self,
        move: ObsidianVaultMoveRequest,
    ) -> ObsidianVaultMoveSkip | None:
        source = resolve_note_path(self._vault_path, move.source_path)
        destination = resolve_note_path(self._vault_path, move.destination_path)
        reason = move.reason.strip()
        if not reason:
            return _move_skip(move, "reason_required")
        if source == destination:
            return _move_skip(move, "source_equals_destination")
        if source.suffix != NOTE_SUFFIX or destination.suffix != NOTE_SUFFIX:
            return _move_skip(move, "only_markdown_notes_can_be_moved")
        if not source.exists():
            return _move_skip(move, "source_missing")
        if not source.is_file():
            return _move_skip(move, "source_not_file")
        if destination.exists():
            return _move_skip(move, "destination_exists")
        return None

    def _applicable_vault_moves(
        self,
        moves: list[ObsidianVaultMoveCandidate],
        skipped: list[ObsidianVaultMoveSkip],
    ) -> list[ObsidianVaultMoveCandidate]:
        applicable: list[ObsidianVaultMoveCandidate] = []
        seen_sources: set[str] = set()
        seen_destinations: set[str] = set()
        for move in moves:
            request = ObsidianVaultMoveRequest(
                source_path=move.source_path,
                destination_path=move.destination_path,
                reason=move.reason,
            )
            if move.source_path in seen_sources:
                skipped.append(_move_skip(request, "duplicate_source"))
                continue
            if move.destination_path in seen_destinations:
                skipped.append(_move_skip(request, "duplicate_destination"))
                continue
            issue = self._move_safety_issue(request)
            if issue is not None:
                skipped.append(issue)
                continue
            seen_sources.add(move.source_path)
            seen_destinations.add(move.destination_path)
            applicable.append(move)
        return applicable

    def _vault_move_report_paths(
        self,
        request: ObsidianVaultMoveApplyRequest,
    ) -> tuple[str, str, Path, Path]:
        base_path = request.report_path or (
            f"{self._alexandria_root}/{LIBRARIAN_OPERATIONS_FOLDER}/Reports/"
            f"vault-move-{conversation_id()}"
        )
        report_stem = base_path.removesuffix(".md").removesuffix(".json")
        markdown_relative = f"{report_stem}.md"
        json_relative = f"{report_stem}.json"
        markdown_path = resolve_note_path(self._vault_path, markdown_relative)
        json_path = resolve_note_path(self._vault_path, json_relative)
        return markdown_relative, json_relative, markdown_path, json_path

    def _ensure_vault_move_report_available(
        self,
        report_paths: tuple[str, str, Path, Path],
    ) -> None:
        _, _, markdown_path, json_path = report_paths
        if markdown_path.exists() or json_path.exists():
            raise ObsidianValidationError("vault move report destination exists")

    def _write_vault_move_report(
        self,
        *,
        report_paths: tuple[str, str, Path, Path],
        status: str,
        moved: list[ObsidianVaultMoveApplied],
        skipped: list[ObsidianVaultMoveSkip],
        verification: ObsidianVaultMoveVerification,
    ) -> tuple[str, str]:
        markdown_relative, json_relative, markdown_path, json_path = report_paths
        self._ensure_vault_move_report_available(report_paths)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(
            _vault_move_report_markdown(
                status=status,
                moved=moved,
                skipped=skipped,
                verification=verification,
            ),
            encoding="utf-8",
        )
        json_path.write_bytes(
            dumps_pretty_json(
                _vault_move_report_json(
                    status=status,
                    moved=moved,
                    skipped=skipped,
                    verification=verification,
                )
            )
        )
        return markdown_relative, json_relative

    def _ensure_vault_layout(self, config: ObsidianVaultConfig) -> None:
        for folder in default_folders(config.alexandria_root):
            resolve_note_path(config.vault_path, folder).mkdir(
                parents=True,
                exist_ok=True,
            )


def _delegate_status(payload: ObsidianLibrarianAsk) -> str:
    if not payload.delegate_to_librarian:
        return "local_only"
    if payload.provider_id or payload.profile_id:
        return "requested_local_fallback"
    return "requested_no_provider_local_fallback"


def _inventory_item_matches(
    item: ObsidianVaultInventoryItem,
    needle: str,
) -> bool:
    haystack = "\n".join(
        [
            item.note_id,
            item.relative_path,
            item.title,
            item.alexandria_type.value,
            item.status,
            item.project or "",
            " ".join(item.tags),
        ]
    ).casefold()
    return needle in haystack


def _move_skip(
    move: ObsidianVaultMoveRequest,
    reason: str,
) -> ObsidianVaultMoveSkip:
    return ObsidianVaultMoveSkip(
        source_path=move.source_path,
        destination_path=move.destination_path,
        reason=reason,
    )


def _loose_note_count(paths: set[Path]) -> int:
    return sum(
        1
        for path in paths
        if path.exists()
        for child in path.iterdir()
        if child.is_file() and child.suffix == NOTE_SUFFIX
    )


def _vault_move_report_json(
    *,
    status: str,
    moved: list[ObsidianVaultMoveApplied],
    skipped: list[ObsidianVaultMoveSkip],
    verification: ObsidianVaultMoveVerification,
) -> JSONObject:
    return {
        "status": status,
        "hard_delete_performed": False,
        "moved": [
            {
                "from": item.source_path,
                "to": item.destination_path,
                "reason": item.reason,
            }
            for item in moved
        ],
        "skipped": [
            {
                "from": item.source_path,
                "to": item.destination_path,
                "reason": item.reason,
            }
            for item in skipped
        ],
        "ambiguous": [],
        "verification": {
            "source_root_loose_notes_remaining": (
                verification.source_root_loose_notes_remaining
            ),
            "reindex_status": verification.reindex_status,
            "verification_hits": verification.verification_hits,
        },
    }


def _vault_move_report_markdown(
    *,
    status: str,
    moved: list[ObsidianVaultMoveApplied],
    skipped: list[ObsidianVaultMoveSkip],
    verification: ObsidianVaultMoveVerification,
) -> str:
    moved_lines = [
        f"- `{item.source_path}` -> `{item.destination_path}` — {item.reason}"
        for item in moved
    ] or ["- none"]
    skipped_lines = [
        f"- `{item.source_path}` -> `{item.destination_path}` — {item.reason}"
        for item in skipped
    ] or ["- none"]
    return "\n".join(
        [
            "# Librarian Vault Move Report",
            "",
            f"- status: `{status}`",
            "- hard_delete_performed: `false`",
            f"- reindex_status: `{verification.reindex_status}`",
            f"- verification_hits: `{verification.verification_hits}`",
            f"- source_root_loose_notes_remaining: `{verification.source_root_loose_notes_remaining}`",
            "",
            "## Moved",
            *moved_lines,
            "",
            "## Skipped",
            *skipped_lines,
            "",
        ]
    )


def _librarian_search_queries(
    *,
    query: str,
    limit: int,
    project: str | None,
    preferred_types: tuple[AlexandriaNoteType, ...],
    excluded_types: tuple[AlexandriaNoteType, ...],
) -> tuple[ObsidianSearchQuery, ...]:
    if preferred_types:
        return tuple(
            ObsidianSearchQuery(
                query=query,
                limit=limit,
                alexandria_type=note_type,
                project=project,
            )
            for note_type in preferred_types
        )
    return (
        ObsidianSearchQuery(
            query=query,
            limit=limit,
            excluded_alexandria_types=list(excluded_types),
            project=project,
        ),
    )


def _selection_excerpt(selection: str | None) -> str | None:
    if selection is None:
        return None
    normalized = selection.strip()
    if not normalized:
        raise ObsidianValidationError("selection_ingestion_failed: selection is blank")
    if len(normalized) <= SELECTION_CONTEXT_MAX_CHARS:
        return normalized
    return f"{normalized[:SELECTION_CONTEXT_MAX_CHARS]}\n…[selection truncated]"


def _librarian_input_context(
    *,
    payload: ObsidianLibrarianAsk,
    active_note: ObsidianNote | None,
    selection_excerpt: str | None,
    source_refs: list[JSONObject],
) -> JSONObject:
    active_note_status = "not_requested" if payload.active_note_path is None else "read"
    selection_status = "not_requested" if selection_excerpt is None else "ingested"
    warnings: list[str] = []
    if not source_refs:
        warnings.append(
            "source_miss_is_not_no_related_notes_without_inventory_verification"
        )
    status = "ready"
    if not source_refs and active_note is None and selection_excerpt is None:
        status = "insufficient_inventory"
    return {
        "status": status,
        "active_note_path": payload.active_note_path,
        "active_note_status": active_note_status,
        "selection_status": selection_status,
        "selection_excerpt": selection_excerpt,
        "source_ref_count": len(source_refs),
        "warnings": warnings,
    }
