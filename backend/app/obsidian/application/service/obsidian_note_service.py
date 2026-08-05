"""Canonical Obsidian note search, read, and save service."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import replace
from pathlib import Path
from typing import Protocol

from app.obsidian.application.graph.obsidian_graph_link_renderer import (
    add_or_update_alexandria_links_section,
)
from app.obsidian.application.notes.obsidian_authoritative_read import (
    authoritative_note_from_path,
)
from app.obsidian.application.notes.obsidian_context_save_policy import (
    apply_context_save_policy,
)
from app.obsidian.application.notes.obsidian_frontmatter_redaction import (
    redacted_frontmatter,
)
from app.obsidian.application.notes.obsidian_note_indexer import note_index_from_path
from app.obsidian.application.notes.obsidian_note_templates import (
    default_note_path,
    frontmatter_for_save,
)
from app.obsidian.application.notes.obsidian_note_write_metadata import (
    apply_write_history,
    frontmatter_for_explicit_write,
    write_is_unchanged,
)
from app.obsidian.application.service.obsidian_vault_lifecycle_service import (
    index_error_code,
)
from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianSaveNote,
    ObsidianSearchQuery,
    ObsidianWriteNote,
)
from app.obsidian.domain.entities.obsidian_note import (
    ObsidianIndexError,
    ObsidianNote,
    ObsidianNoteWriteResult,
    ObsidianReindexResult,
    ObsidianSearchHit,
)
from app.obsidian.domain.event_enum.obsidian_enums import (
    AlexandriaNoteType,
    ObsidianFrontmatterMode,
    ObsidianIndexErrorCode,
    ObsidianWriteMatchBy,
    ObsidianWriteMode,
    ObsidianWriteOperation,
)
from app.obsidian.domain.repositories.obsidian_repository import (
    IObsidianIndexRepository,
)
from app.obsidian.infrastructure.markdown.atomic_markdown_write import (
    atomic_write_markdown,
)
from app.obsidian.infrastructure.markdown.frontmatter import (
    frontmatter_text,
    parse_markdown_document,
    render_markdown_document,
)
from app.obsidian.infrastructure.markdown.paths import (
    resolve_note_path,
    safe_relative_path,
)
from app.obsidian.infrastructure.obsidian_vault_config_store import (
    ObsidianVaultConfigStore,
)
from app.shared.exceptions.obsidian_exceptions import (
    ObsidianIdentityConflictError,
    ObsidianIndexWriteError,
    ObsidianNotFoundError,
    ObsidianValidationError,
    ObsidianWriteConflictError,
    ObsidianWriteTargetNotFoundError,
)
from app.shared.infrastructure.identifiers import new_uuid
from app.shared.types.types_convert_utils import now_utc
from app.shared.utils.secret_redaction import redact_secret_text


class ObsidianNoteSupersedeHook(Protocol):
    """Reconcile Context supersede metadata after a canonical save."""

    async def __call__(
        self,
        *,
        superseded_context_id: str,
        replacement_context_id: str,
    ) -> None:
        """Mark one Context as superseded.

        Args:
            superseded_context_id: Context being replaced.
            replacement_context_id: Canonical replacement Context.
        """


class ObsidianNoteService:
    """Own canonical note access, Markdown persistence, and index write-through."""

    def __init__(
        self,
        *,
        repository: IObsidianIndexRepository,
        vault_config_store: ObsidianVaultConfigStore,
        reindex: Callable[[], Awaitable[ObsidianReindexResult]],
        mark_context_superseded: ObsidianNoteSupersedeHook,
    ) -> None:
        """Create the canonical note service.

        Args:
            repository: Rebuildable SQLite index repository.
            vault_config_store: Runtime vault location provider.
            reindex: Vault index refresh callback.
            mark_context_superseded: Context lifecycle reconciliation callback.
        """
        self._repository = repository
        self._vault_config_store = vault_config_store
        self._reindex = reindex
        self._mark_context_superseded = mark_context_superseded
        self._write_lock = asyncio.Lock()

    async def search(
        self,
        query: ObsidianSearchQuery,
        *,
        refresh: bool = False,
    ) -> list[ObsidianSearchHit]:
        """Search Obsidian notes through the SQLite index.

        Args:
            query: Search filters and query text.
            refresh: Whether to re-scan the vault before querying.

        Returns:
            Ranked search hits.
        """
        if refresh:
            await self._reindex()
        return await self._repository.search(query)

    async def read_note(self, note_id: str) -> ObsidianNote:
        """Read one managed note by stable id and reload its Markdown body.

        Args:
            note_id: Stable note id from frontmatter.

        Returns:
            Authoritative note loaded from Markdown.
        """
        config = self._vault_config_store.current()
        indexed = await self._repository.get_by_id(note_id)
        if indexed is None:
            await self._reindex()
            indexed = await self._repository.get_by_id(note_id)
        if indexed is None:
            raise ObsidianNotFoundError(f"Obsidian note not found: {note_id}")
        return authoritative_note_from_path(
            vault_path=config.vault_path,
            relative_path=indexed.relative_path,
            alexandria_root=config.alexandria_root,
            indexed=indexed,
        )

    async def read_note_by_path(self, relative_path: str) -> ObsidianNote:
        """Read one managed note by vault-relative path.

        Args:
            relative_path: Vault-relative Markdown path.

        Returns:
            Authoritative note loaded from Markdown.
        """
        config = self._vault_config_store.current()
        safe_path = str(safe_relative_path(relative_path))
        indexed = await self._repository.get_by_path(safe_path)
        if indexed is None:
            await self._reindex()
            indexed = await self._repository.get_by_path(safe_path)
        if indexed is None:
            raise ObsidianNotFoundError(f"Obsidian note not found: {safe_path}")
        return authoritative_note_from_path(
            vault_path=config.vault_path,
            relative_path=safe_path,
            alexandria_root=config.alexandria_root,
            indexed=indexed,
        )

    async def save_note(self, payload: ObsidianSaveNote) -> ObsidianNote:
        """Create or replace one Alexandria-managed Markdown note.

        Args:
            payload: Save request with body and metadata.

        Returns:
            Saved note loaded through the index.
        """
        async with self._write_lock:
            note, _ = await self._save_note_serialized(payload)
            return note

    async def write_note(
        self,
        command: ObsidianWriteNote,
    ) -> ObsidianNoteWriteResult:
        """Execute an explicit create, update, or upsert without identity guessing.

        Args:
            command: Value supplied to write_note.

        Returns:
            Result produced by write_note.
        """
        async with self._write_lock:
            (
                payload,
                existing,
                expected_operation,
            ) = await self._resolve_explicit_write_target(command)
            note, mutated = await self._save_note_serialized(
                payload,
                existing_note=existing,
                frontmatter_mode=command.frontmatter_mode,
            )
        operation = expected_operation if mutated else ObsidianWriteOperation.UNCHANGED
        return ObsidianNoteWriteResult(
            operation=operation,
            write_mode=command.write_mode,
            match_by=command.match_by,
            note=note,
            storage_status="stored" if mutated else "unchanged",
            metadata_status="indexed",
            fts_status="indexed",
            sqlite_graph_edge_status="indexed",
            graph_projection_status="stale" if mutated else "unknown",
            reindex_required=mutated,
        )

    async def _save_note_serialized(
        self,
        payload: ObsidianSaveNote,
        *,
        existing_note: ObsidianNote | None = None,
        frontmatter_mode: ObsidianFrontmatterMode | None = None,
    ) -> tuple[ObsidianNote, bool]:
        """Save one note while serializing canonical read-check-replace writes."""
        config = self._vault_config_store.current()
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
            root=config.alexandria_root,
            note_type=payload.alexandria_type,
            title=title,
        )
        safe_path = str(safe_relative_path(relative_path))
        absolute = resolve_note_path(config.vault_path, safe_path)
        indexed_note = await self._repository.get_by_path(safe_path)
        self._validate_expected_content_hash(
            payload=payload,
            indexed_note=indexed_note,
            safe_path=safe_path,
        )
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
            or self.note_id_from_existing_file(absolute)
            or new_uuid()
        )
        id_match = await self._repository.get_by_id(note_id)
        if id_match is not None and id_match.relative_path != safe_path:
            raise ObsidianValidationError(
                f"DUPLICATE_CONTEXT_ID: {note_id} is already used by "
                f"{id_match.relative_path}"
            )
        absolute.parent.mkdir(parents=True, exist_ok=True)
        warnings = [*redaction.warnings, *frontmatter_warnings]
        if frontmatter_mode is None:
            frontmatter = frontmatter_for_save(
                payload,
                note_id=note_id,
                title=title,
                redaction_warnings=warnings,
            )
        else:
            frontmatter = frontmatter_for_explicit_write(
                payload,
                note_id=note_id,
                title=title,
                existing=existing_note,
                mode=frontmatter_mode,
                redaction_warnings=warnings,
            )
        body = add_or_update_alexandria_links_section(
            redaction.redacted_content,
            frontmatter,
        )
        if (
            frontmatter_mode is not None
            and existing_note is not None
            and write_is_unchanged(
                existing=existing_note,
                desired_frontmatter=frontmatter,
                desired_body=body,
            )
        ):
            return existing_note, False
        if frontmatter_mode is not None:
            frontmatter = apply_write_history(
                frontmatter,
                existing=existing_note,
                body=body,
            )
        supersedes_context_id: str | None = None
        if payload.alexandria_type is AlexandriaNoteType.CONTEXT:
            policy = await apply_context_save_policy(
                payload,
                note_id,
                frontmatter,
                body,
                self._repository,
            )
            if policy.duplicate is not None:
                return policy.duplicate, False
            frontmatter = policy.frontmatter
            supersedes_context_id = policy.supersedes_context_id
        document = render_markdown_document(frontmatter, body)
        atomic_write_markdown(absolute, document)
        index_payload = note_index_from_path(
            absolute,
            safe_path,
            alexandria_root=config.alexandria_root,
        )
        if index_payload is None:
            raise ObsidianValidationError(
                "saved note is missing Alexandria frontmatter"
            )
        try:
            note = await self._repository.upsert_note(index_payload)
        except ObsidianIndexWriteError as exc:
            index_error = ObsidianIndexError(
                note_path=safe_path,
                context_id=note_id,
                error_code=ObsidianIndexErrorCode.INDEX_WRITE_FAILED,
                error_message=str(exc),
                detected_at=now_utc(),
            )
            await self._repository.record_index_error(index_error)
            raise ObsidianValidationError(
                "INDEX_WRITE_FAILED: canonical Markdown was preserved for reindex"
            ) from exc
        if (
            payload.alexandria_type is AlexandriaNoteType.CONTEXT
            and supersedes_context_id is not None
        ):
            try:
                await self._mark_context_superseded(
                    superseded_context_id=supersedes_context_id,
                    replacement_context_id=note.note_id,
                )
            except (OSError, ObsidianValidationError) as exc:
                index_error = ObsidianIndexError(
                    note_path=safe_path,
                    context_id=note.note_id,
                    error_code=index_error_code(exc),
                    error_message=str(exc),
                    detected_at=now_utc(),
                )
                await self._repository.record_index_error(index_error)
                raise ObsidianValidationError(
                    "INDEX_WRITE_FAILED: replacement Markdown was preserved for "
                    "reindex reconciliation"
                ) from exc
        return note, True

    async def _resolve_explicit_write_target(
        self,
        command: ObsidianWriteNote,
    ) -> tuple[ObsidianSaveNote, ObsidianNote | None, ObsidianWriteOperation]:
        """Resolve exact selectors and reject every ambiguity before mutation."""
        payload = command.note
        if command.match_by is ObsidianWriteMatchBy.NOTE_ID and payload.note_id is None:
            raise ObsidianValidationError("note_id is required when match_by=note_id")
        if (
            command.match_by is ObsidianWriteMatchBy.PATH
            and payload.relative_path is None
        ):
            raise ObsidianValidationError("path is required when match_by=path")
        title = payload.title.strip()
        if not title:
            raise ObsidianValidationError("title is required")
        config = self._vault_config_store.current()
        requested_path = payload.relative_path
        resolved_path = requested_path or default_note_path(
            root=config.alexandria_root,
            note_type=payload.alexandria_type,
            title=title,
        )
        safe_path = str(safe_relative_path(resolved_path))
        absolute = resolve_note_path(config.vault_path, safe_path)
        by_path = await self._repository.get_by_path(safe_path)
        by_id = (
            None
            if payload.note_id is None
            else await self._repository.get_by_id(payload.note_id)
        )
        path_selector_relevant = (
            requested_path is not None
            or command.match_by is ObsidianWriteMatchBy.PATH
            or command.write_mode is ObsidianWriteMode.CREATE
        )
        needs_refresh = (
            path_selector_relevant and absolute.exists() and by_path is None
        ) or (payload.note_id is not None and by_id is None)
        if needs_refresh:
            await self._reindex()
            by_path = await self._repository.get_by_path(safe_path)
            by_id = (
                None
                if payload.note_id is None
                else await self._repository.get_by_id(payload.note_id)
            )

        if (
            path_selector_relevant
            and by_id is not None
            and by_path is not None
            and by_id.note_id != by_path.note_id
        ):
            self._raise_identity_conflict(command, safe_path, by_id, by_path)

        if command.write_mode is ObsidianWriteMode.CREATE:
            if by_id is not None or by_path is not None or absolute.exists():
                self._raise_identity_conflict(command, safe_path, by_id, by_path)
            return (
                replace(payload, relative_path=safe_path),
                None,
                ObsidianWriteOperation.CREATED,
            )

        target = by_id if command.match_by is ObsidianWriteMatchBy.NOTE_ID else by_path
        if (
            target is not None
            and requested_path is not None
            and target.relative_path != safe_path
        ):
            self._raise_identity_conflict(command, safe_path, by_id, by_path)
        if (
            target is not None
            and payload.note_id is not None
            and target.note_id != payload.note_id
        ):
            self._raise_identity_conflict(command, safe_path, by_id, by_path)

        if target is None and command.write_mode is ObsidianWriteMode.UPDATE:
            raise ObsidianWriteTargetNotFoundError(
                requested_note_id=payload.note_id,
                requested_path=requested_path,
            )
        if target is None:
            if by_id is not None or by_path is not None or absolute.exists():
                self._raise_identity_conflict(command, safe_path, by_id, by_path)
            return (
                replace(payload, relative_path=safe_path),
                None,
                ObsidianWriteOperation.CREATED,
            )

        return (
            replace(
                _preserve_omitted_update_fields(
                    payload,
                    existing=target,
                    provided_fields=command.provided_fields,
                ),
                note_id=target.note_id,
                relative_path=target.relative_path,
            ),
            target,
            ObsidianWriteOperation.UPDATED,
        )

    @staticmethod
    def _raise_identity_conflict(
        command: ObsidianWriteNote,
        safe_path: str,
        id_target: ObsidianNote | None,
        path_target: ObsidianNote | None,
    ) -> None:
        raise ObsidianIdentityConflictError(
            operation=command.write_mode.value,
            requested_note_id=command.note.note_id,
            requested_path=safe_path,
            id_target_path=None if id_target is None else id_target.relative_path,
            path_target_id=None if path_target is None else path_target.note_id,
            recommended_operation=(
                "update"
                if command.write_mode is ObsidianWriteMode.CREATE
                else "resolve_identity"
            ),
        )

    @staticmethod
    def _validate_expected_content_hash(
        *,
        payload: ObsidianSaveNote,
        indexed_note: ObsidianNote | None,
        safe_path: str,
    ) -> None:
        """Reject a stale compare-and-swap token before replacing Markdown."""
        expected = payload.expected_content_hash
        if expected is None:
            return
        if indexed_note is None:
            raise ObsidianWriteConflictError(
                f"OBSIDIAN_WRITE_CONFLICT: note does not exist: {safe_path}"
            )
        if indexed_note.content_hash != expected:
            raise ObsidianWriteConflictError(
                "OBSIDIAN_WRITE_CONFLICT: expected content hash does not match "
                f"the current note: {safe_path}"
            )

    def note_id_from_existing_file(self, path: Path) -> str | None:
        """Read a stable note id from an existing managed Markdown file.

        Args:
            path: Candidate Markdown path.

        Returns:
            Stable frontmatter id when safely readable.
        """
        if not path.exists() or path.is_symlink():
            return None
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return None
        try:
            document = parse_markdown_document(text)
        except ValueError:
            return None
        return frontmatter_text(document.frontmatter, "id")


def _preserve_omitted_update_fields(
    payload: ObsidianSaveNote,
    *,
    existing: ObsidianNote,
    provided_fields: frozenset[str] | None,
) -> ObsidianSaveNote:
    """Retain existing optional fields omitted at the external update boundary."""
    if provided_fields is None:
        return payload
    return replace(
        payload,
        tags=payload.tags if "tags" in provided_fields else existing.tags,
        status=payload.status if "status" in provided_fields else existing.status,
        project=payload.project if "project" in provided_fields else existing.project,
        source=(
            payload.source
            if "source" in provided_fields
            else existing.source or payload.source
        ),
    )
