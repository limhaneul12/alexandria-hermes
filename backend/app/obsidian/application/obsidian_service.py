"""Application service for Obsidian-backed Alexandria notes."""

from __future__ import annotations

from pathlib import Path

from app.obsidian.application.obsidian_graph_relations import (
    add_or_update_alexandria_links_section,
)
from app.obsidian.application.obsidian_note_indexer import note_index_from_path
from app.obsidian.application.obsidian_note_templates import (
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
)
from app.obsidian.domain.entities.obsidian_note import (
    ObsidianNote,
    ObsidianReindexResult,
    ObsidianSearchHit,
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
    resolve_vault_path,
    safe_relative_path,
)
from app.shared.exceptions import ObsidianNotFoundError, ObsidianValidationError
from app.shared.infrastructure.identifiers import new_uuid
from app.shared.types.extra_types import JSONObject
from app.shared.utils.secret_redaction import redact_secret_text


class ObsidianService:
    """Coordinate Obsidian vault IO and rebuildable SQLite indexing."""

    def __init__(
        self,
        *,
        repository: IObsidianIndexRepository,
        vault_path: str,
        alexandria_root: str = "Alexandria",
    ) -> None:
        """Initialize service dependencies.

        Args:
            repository: Rebuildable SQLite index repository.
            vault_path: Obsidian vault root.
            alexandria_root: Managed folder inside the vault.
        """
        self._repository = repository
        self._vault_path = resolve_vault_path(vault_path)
        self._alexandria_root = str(safe_relative_path(alexandria_root))

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
        return self._read_authoritative_note(indexed.relative_path, indexed=indexed)

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
        return self._read_authoritative_note(safe_path, indexed=indexed)

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
            redaction_warnings=redaction.warnings,
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
        preferred = (
            payload.preferred_alexandria_types[0]
            if payload.preferred_alexandria_types
            else None
        )
        search_query = ObsidianSearchQuery(
            query="\n".join(
                part
                for part in [payload.query, payload.selection]
                if part is not None and part.strip()
            ),
            limit=5,
            alexandria_type=preferred,
            project=payload.project,
        )
        hits = await self.search(search_query)
        active_note = await self._active_note_or_none(payload.active_note_path)
        answer = librarian_answer(payload, hits, active_note)
        source_refs = source_refs_for_librarian(hits, active_note)
        response: JSONObject = {
            "answer_markdown": answer,
            "source_refs": source_refs,
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
        if payload.save_transcript:
            transcript = await self._save_librarian_chat(
                payload, answer, hits, response
            )
            response["transcript_path"] = transcript.relative_path
        return response

    async def _active_note_or_none(
        self, relative_path: str | None
    ) -> ObsidianNote | None:
        if not relative_path:
            return None
        try:
            return await self.read_note_by_path(relative_path)
        except ObsidianNotFoundError:
            return None

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
                    f"{self._alexandria_root}/Librarian/Chats/{conversation_id}.md"
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

    def _root_path(self) -> Path:
        return resolve_note_path(self._vault_path, self._alexandria_root)

    def _read_authoritative_note(
        self,
        relative_path: str,
        *,
        indexed: ObsidianNote,
    ) -> ObsidianNote:
        absolute = resolve_note_path(self._vault_path, relative_path)
        if not absolute.exists():
            raise ObsidianNotFoundError(f"Obsidian note not found: {relative_path}")
        payload = note_index_from_path(
            absolute,
            relative_path,
            alexandria_root=self._alexandria_root,
        )
        if payload is None:
            raise ObsidianValidationError(
                f"Obsidian note is missing Alexandria frontmatter: {relative_path}"
            )
        return ObsidianNote(
            note_id=payload.note_id,
            relative_path=payload.relative_path,
            alexandria_type=payload.alexandria_type,
            title=payload.title,
            status=payload.status,
            tags=payload.tags,
            project=payload.project,
            source=payload.source,
            content_hash=payload.content_hash,
            frontmatter=payload.frontmatter,
            body=payload.body,
            index_status=indexed.index_status,
            error_message=indexed.error_message,
            size_bytes=payload.size_bytes,
            modified_at=payload.modified_at,
            indexed_at=indexed.indexed_at,
        )


def _delegate_status(payload: ObsidianLibrarianAsk) -> str:
    if not payload.delegate_to_librarian:
        return "local_only"
    if payload.provider_id or payload.profile_id:
        return "requested_local_fallback"
    return "requested_no_provider_local_fallback"
