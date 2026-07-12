"""Obsidian vault service behavior tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import anyio
from app.librarian.domain.contracts.hermes_collaboration_contracts import (
    HermesLibrarianAskCommand,
)
from app.librarian.domain.event_enum.collaboration_enums import (
    AcquisitionDecision,
    LibrarianDelegateKind,
    LibrarianDelegateStatus,
    LibrarianDelegationStatus,
)
from app.librarian.domain.types.hermes_collaboration_payload_types import (
    HermesLibrarianAskPayload,
)
from app.main import app
from app.memory.application.memory_compact_service import MemoryCompactService
from app.memory.domain.event_enum.memory_compact_enums import MemoryCompactStatus
from app.memory.domain.repositories.memory_compact_repository import (
    MemoryCompactCreate,
    MemoryCompactSourceRefCreate,
)
from app.memory.infrastructure.repositories.memory_compact_repository import (
    ObsidianMemoryCompactRepository,
)
from app.obsidian.application.obsidian_librarian_job_service import (
    ObsidianLibrarianJobService,
)
from app.obsidian.application.obsidian_service import ObsidianService
from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianChunkIndex,
    ObsidianLibrarianAsk,
    ObsidianNoteIndex,
    ObsidianSaveNote,
    ObsidianSearchQuery,
    ObsidianVaultInventoryRequest,
    ObsidianVaultMoveApplyRequest,
    ObsidianVaultMovePlanRequest,
    ObsidianVaultMoveRequest,
    ObsidianVaultSettingsUpdate,
)
from app.obsidian.domain.event_enum.obsidian_enums import (
    AlexandriaNoteType,
    ObsidianIndexStatus,
    ObsidianLibrarianJobStatus,
)
from app.obsidian.infrastructure.models import (
    obsidian_index_models as _obsidian_index_models,
)
from app.obsidian.infrastructure.models.obsidian_index_models import ObsidianFileORM
from app.obsidian.infrastructure.obsidian_vault_config_store import (
    ObsidianVaultConfigStore,
)
from app.obsidian.infrastructure.repositories.obsidian_index_repository import (
    SqlAlchemyObsidianIndexRepository,
)
from app.shared.exceptions import ObsidianNotFoundError, ObsidianValidationError
from app.shared.infrastructure.database import Database
from app.shared.serialization.orjson_codec import loads_json
from dependency_injector import providers
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession

_OBSIDIAN_MODELS_LOADED = _obsidian_index_models


def _database_url(path: Path) -> str:
    return f"sqlite+aiosqlite:///{path}"


async def _service(tmp_path: Path) -> tuple[Database, AsyncSession, ObsidianService]:
    database = Database(
        database_url=_database_url(tmp_path / "obsidian.db"), create_schema=True
    )
    await database.initialize()
    session = database.session()
    service = ObsidianService(
        repository=SqlAlchemyObsidianIndexRepository(session=session),
        vault_path=str(tmp_path / "vault"),
        alexandria_root="Alexandria",
    )
    return database, session, service


class _RecordingDelegateService:
    """Test double that behaves like a selected provider-backed librarian."""

    def __init__(self) -> None:
        self.command: HermesLibrarianAskCommand | None = None

    async def ask_librarian(
        self,
        command: HermesLibrarianAskCommand,
    ) -> HermesLibrarianAskPayload:
        self.command = command
        return HermesLibrarianAskPayload(
            job_id="librarian-job-test",
            status=LibrarianDelegationStatus.COMPLETED,
            decision=AcquisitionDecision.DELEGATE_TO_LIBRARIAN,
            librarian_available=True,
            self_acquisition_allowed=True,
            recommendation="delegate complete",
            provider_id="auto-provider",
            candidate_id=None,
            librarian_profile_id="auto-profile",
            librarian_model=None,
            librarian_role_prompt=None,
            max_librarian_agents=1,
            route_preview=["Specialized librarian provider: auto-provider"],
            selected_profiles=["auto-profile"],
            matched_specialties=["obsidian"],
            quality_review_added=False,
            routing_reason="test route",
            delegates=[
                {
                    "profile_id": "auto-profile",
                    "provider_id": "auto-provider",
                    "status": LibrarianDelegateStatus.COMPLETED,
                    "delegate_type": LibrarianDelegateKind.LIBRARY_SEARCH,
                    "summary": "provider-backed compact guidance",
                    "matched_specialties": ["obsidian"],
                }
            ],
        )


def test_obsidian_init_creates_frontmatter_start_note(tmp_path: Path) -> None:
    """Initializing the vault should create a managed START_HERE note."""

    async def scenario() -> None:
        database, session, service = await _service(tmp_path)
        try:
            note = await service.initialize_vault()
            status = await service.status()
        finally:
            await session.close()
            await database.shutdown()

        note_path = tmp_path / "vault" / "Alexandria" / "START_HERE.md"
        note_text = note_path.read_text(encoding="utf-8")
        assert note.note_id == "alexandria_start_here"
        assert status.indexed_notes == 1
        assert "alexandria_type: context" in note_text
        assert "id: alexandria_start_here" in note_text
        assert not (tmp_path / "vault" / "Alexandria" / "Librarian").exists()
        assert (
            tmp_path / "vault" / "Alexandria" / "_Ops" / "Librarian" / "Chats"
        ).exists()
        assert (
            tmp_path / "vault" / "Alexandria" / "_Ops" / "Librarian" / "Reports"
        ).exists()
        assert (tmp_path / "vault" / "Alexandria" / "_Inbox" / "Captures").exists()
        assert (tmp_path / "vault" / "Alexandria" / "_Inbox" / "To Promote").exists()
        assert (tmp_path / "vault" / "Alexandria" / "Contexts" / "Projects").exists()
        assert not (
            tmp_path / "vault" / "Alexandria" / "Contexts" / "Project Context"
        ).exists()

    anyio.run(scenario)


def test_obsidian_reindex_searches_frontmatter_notes(tmp_path: Path) -> None:
    """Reindex should classify official notes and search them through SQLite FTS."""

    async def scenario() -> None:
        database, session, service = await _service(tmp_path)
        try:
            notes_dir = tmp_path / "vault" / "Alexandria" / "Contexts" / "Decisions"
            notes_dir.mkdir(parents=True)
            (notes_dir / "Storage.md").write_text(
                "---\n"
                "alexandria_type: context\n"
                "id: ctx_storage\n"
                "title: Obsidian Storage\n"
                "tags:\n"
                "  - obsidian\n"
                "status: active\n"
                "created_at: '2026-05-25'\n"
                "source: human\n"
                "project: alexandria-hermes\n"
                "---\n\n"
                "# Obsidian Storage\n\nSQLite is a rebuildable search cache.\n",
                encoding="utf-8",
            )
            result = await service.reindex()
            hits = await service.search(
                ObsidianSearchQuery(query="rebuildable search cache", limit=3),
                refresh=False,
            )
        finally:
            await session.close()
            await database.shutdown()

        assert result.files_seen == 1
        assert result.files_indexed == 1
        assert [(hit.note.note_id, hit.note.relative_path) for hit in hits] == [
            ("ctx_storage", "Alexandria/Contexts/Decisions/Storage.md")
        ]

    anyio.run(scenario)


def test_obsidian_search_excludes_stale_notes_after_reindex(tmp_path: Path) -> None:
    """Search should not surface paths that were marked stale by a later scan."""

    async def scenario() -> list[str]:
        database, session, service = await _service(tmp_path)
        try:
            await service.save_note(
                ObsidianSaveNote(
                    title="Temporary Librarian Chat",
                    body="# Temporary Librarian Chat\n\nstale search marker",
                    alexandria_type=AlexandriaNoteType.LIBRARIAN_CHAT,
                    note_id="librarian_chat_temporary_stale",
                )
            )
            stale_path = (
                tmp_path
                / "vault"
                / "Alexandria"
                / "_Ops"
                / "Librarian"
                / "Chats"
                / "Temporary Librarian Chat.md"
            )
            stale_path.unlink()
            await service.reindex()
            hits = await service.search(
                ObsidianSearchQuery(
                    query="stale search marker",
                    alexandria_type=AlexandriaNoteType.LIBRARIAN_CHAT,
                ),
                refresh=False,
            )
        finally:
            await session.close()
            await database.shutdown()

        return [hit.note.relative_path for hit in hits]

    assert anyio.run(scenario) == []


def test_obsidian_search_filters_stale_notes_before_fts_limit(
    tmp_path: Path,
) -> None:
    """Stale FTS rows should not crowd indexed notes out of limited searches."""

    async def scenario() -> list[str]:
        database, session, service = await _service(tmp_path)
        try:
            for index in range(3):
                await service.save_note(
                    ObsidianSaveNote(
                        title=f"Temporary stale chat {index}",
                        body=(
                            f"# Temporary stale chat {index}\n\n"
                            "crowdouttoken crowdouttoken crowdouttoken"
                        ),
                        alexandria_type=AlexandriaNoteType.LIBRARIAN_CHAT,
                        note_id=f"librarian_chat_stale_crowdout_{index}",
                    )
                )
            await service.save_note(
                ObsidianSaveNote(
                    title="Durable context kept",
                    body="# Durable context kept\n\ncrowdouttoken",
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="ctx_durable_crowdout",
                )
            )
            stale_chat_dir = (
                tmp_path / "vault" / "Alexandria" / "_Ops" / "Librarian" / "Chats"
            )
            for stale_path in stale_chat_dir.glob("Temporary stale chat*.md"):
                stale_path.unlink()
            await service.reindex()
            hits = await service.search(
                ObsidianSearchQuery(query="crowdouttoken", limit=1),
                refresh=False,
            )
        finally:
            await session.close()
            await database.shutdown()

        return [hit.note.note_id for hit in hits]

    assert anyio.run(scenario) == ["ctx_durable_crowdout"]


def test_obsidian_reindex_handles_note_id_change_for_same_path(
    tmp_path: Path,
) -> None:
    """Reindex should replace stale path rows when frontmatter id changes."""

    async def scenario() -> tuple[int, int, str, bool]:
        database, session, service = await _service(tmp_path)
        try:
            notes_dir = tmp_path / "vault" / "Alexandria" / "Contexts" / "Decisions"
            notes_dir.mkdir(parents=True)
            note_path = notes_dir / "Storage.md"
            note_path.write_text(
                "---\n"
                "alexandria_type: context\n"
                "id: ctx_storage_old\n"
                "title: Obsidian Storage\n"
                "tags:\n"
                "  - obsidian\n"
                "status: active\n"
                "source: human\n"
                "project: alexandria-hermes\n"
                "---\n\n"
                "# Obsidian Storage\n\nOriginal id.\n",
                encoding="utf-8",
            )
            first = await service.reindex()
            note_path.write_text(
                "---\n"
                "alexandria_type: context\n"
                "id: ctx_storage_new\n"
                "title: Obsidian Storage\n"
                "tags:\n"
                "  - obsidian\n"
                "status: active\n"
                "source: human\n"
                "project: alexandria-hermes\n"
                "---\n\n"
                "# Obsidian Storage\n\nRenamed id.\n",
                encoding="utf-8",
            )
            second = await service.reindex()
            renamed = await service.read_note("ctx_storage_new")
            try:
                await service.read_note("ctx_storage_old")
            except ObsidianNotFoundError:
                old_id_missing = True
            else:
                old_id_missing = False
        finally:
            await session.close()
            await database.shutdown()
        return first.files_indexed, second.files_indexed, renamed.body, old_id_missing

    first_indexed, second_indexed, body, old_id_missing = anyio.run(scenario)

    assert first_indexed == 1
    assert second_indexed == 1
    assert "Renamed id." in body
    assert old_id_missing is True


def test_obsidian_reindex_reads_existing_embeddings_before_file_row_flush(
    tmp_path: Path,
) -> None:
    """Replacing chunks should not autoflush dirty file metadata before reads."""

    def payload(*, title: str, content_hash: str) -> ObsidianNoteIndex:
        return ObsidianNoteIndex(
            note_id="autoflush-note",
            relative_path="Alexandria/Notes/Autoflush.md",
            alexandria_type=AlexandriaNoteType.CONTEXT,
            title=title,
            status="active",
            tags=["sqlite"],
            project="alexandria-hermes",
            source="test",
            content_hash=content_hash,
            frontmatter={"id": "autoflush-note", "title": title},
            body=f"# {title}\n\nBody",
            size_bytes=42,
            modified_at=datetime.now(UTC),
            chunks=[
                ObsidianChunkIndex(
                    chunk_index=0,
                    heading_path=None,
                    text=f"{title} body",
                    content_hash=content_hash,
                    token_count=2,
                )
            ],
        )

    async def scenario() -> list[str]:
        database = Database(
            database_url=_database_url(tmp_path / "obsidian.db"), create_schema=True
        )
        await database.initialize()
        session = database.session()
        statements: list[str] = []

        def record_statement(
            _connection, _cursor, statement, _parameters, *_args
        ) -> None:
            normalized = " ".join(str(statement).lower().split())
            if normalized.startswith("select obsidian_chunks"):
                statements.append("select_chunks")
            if normalized.startswith("update obsidian_files"):
                statements.append("update_file")

        event.listen(
            database.engine.sync_engine, "before_cursor_execute", record_statement
        )
        try:
            repository = SqlAlchemyObsidianIndexRepository(session=session)
            await repository.upsert_note(
                payload(title="Initial", content_hash="hash-a")
            )
            await session.commit()
            statements.clear()

            await repository.upsert_note(
                payload(title="Updated", content_hash="hash-b")
            )
            await session.commit()
            return statements
        finally:
            event.remove(
                database.engine.sync_engine, "before_cursor_execute", record_statement
            )
            await session.close()
            await database.shutdown()

    statements = anyio.run(scenario)

    assert "select_chunks" in statements
    assert "update_file" in statements
    assert statements.index("select_chunks") < statements.index("update_file")


def test_obsidian_save_note_writes_markdown_and_reindexes(tmp_path: Path) -> None:
    """Saving a note should write canonical Markdown and make it searchable."""

    async def scenario() -> None:
        database, session, service = await _service(tmp_path)
        try:
            saved = await service.save_note(
                ObsidianSaveNote(
                    title="Web Research Skill",
                    body="# Web Research Skill\n\nSearch official sources before answering.",
                    alexandria_type=AlexandriaNoteType.SKILL,
                    note_id="skill_web_research",
                    tags=["research", "web-search"],
                    project="alexandria-hermes",
                    source="human",
                )
            )
            hits = await service.search(
                ObsidianSearchQuery(
                    query="official sources",
                    alexandria_type=AlexandriaNoteType.SKILL,
                ),
                refresh=False,
            )
        finally:
            await session.close()
            await database.shutdown()

        note_path = tmp_path / "vault" / saved.relative_path
        assert note_path.exists()
        assert saved.relative_path == "Alexandria/Skills/Drafts/Web Research Skill.md"
        assert hits[0].note.note_id == "skill_web_research"

    anyio.run(scenario)


def test_obsidian_vault_settings_update_redirects_future_writes(
    tmp_path: Path,
) -> None:
    """Runtime vault settings should persist and move future note writes."""

    async def scenario() -> tuple[str, str, bool, bool, str | None]:
        database = Database(
            database_url=_database_url(tmp_path / "obsidian.db"), create_schema=True
        )
        await database.initialize()
        session = database.session()
        config_path = tmp_path / "vault-config.json"
        target_vault = tmp_path / "Desktop" / "Alexandria"
        store = ObsidianVaultConfigStore(
            default_vault_path=str(tmp_path / "generated-vault"),
            default_alexandria_root="Alexandria",
            config_path=str(config_path),
        )
        service = ObsidianService(
            repository=SqlAlchemyObsidianIndexRepository(session=session),
            vault_config_store=store,
        )
        try:
            status = await service.configure_vault_settings(
                ObsidianVaultSettingsUpdate(
                    vault_path=str(target_vault),
                    alexandria_root=".",
                    initialize=True,
                    reindex=True,
                )
            )
            saved = await service.save_note(
                ObsidianSaveNote(
                    title="Configured Vault Note",
                    body="# Configured Vault Note\n\nSaved from plugin settings.",
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="ctx_configured_vault_note",
                )
            )
            persisted = loads_json(config_path.read_bytes())
            persisted_path = (
                persisted["vault_path"] if isinstance(persisted, dict) else None
            )
        finally:
            await session.close()
            await database.shutdown()
        return (
            status.vault_path,
            status.alexandria_root,
            (target_vault / "START_HERE.md").exists(),
            (target_vault / saved.relative_path).exists(),
            persisted_path if isinstance(persisted_path, str) else None,
        )

    status_path, alexandria_root, start_exists, note_exists, persisted_path = anyio.run(
        scenario
    )

    assert status_path == str((tmp_path / "Desktop" / "Alexandria").resolve())
    assert alexandria_root == "."
    assert start_exists is True
    assert note_exists is True
    assert persisted_path == status_path


def test_obsidian_roundtrips_memory_skill_prompt_after_sqlite_rebuild(
    tmp_path: Path,
) -> None:
    """Canonical artifact notes should survive SQLite cache deletion/rebuild."""

    async def scenario() -> None:
        vault_path = tmp_path / "vault"
        memory_service = MemoryCompactService(
            repository=ObsidianMemoryCompactRepository(
                vault_path=vault_path,
                relative_dir="Alexandria/Memory Compacts",
            )
        )
        compact = await memory_service.create(
            MemoryCompactCreate(
                project="alexandria-hermes",
                covered_from=datetime(2026, 5, 25, tzinfo=UTC),
                covered_to=datetime(2026, 5, 26, tzinfo=UTC),
                markdown_body=(
                    "# Current Memory Compact\n\n"
                    "Obsidian canonical memory survives SQLite rebuild."
                ),
                status=MemoryCompactStatus.CURRENT,
                source_refs=[
                    MemoryCompactSourceRefCreate(
                        source_type="context",
                        source_id="ctx-storage",
                        title="Storage decision",
                        detail_path="Alexandria/Contexts/Decisions/Storage.md",
                    )
                ],
            )
        )

        first_database = Database(
            database_url=_database_url(tmp_path / "first.db"),
            create_schema=True,
        )
        await first_database.initialize()
        first_session = first_database.session()
        try:
            first_service = ObsidianService(
                repository=SqlAlchemyObsidianIndexRepository(session=first_session),
                vault_path=str(vault_path),
                alexandria_root="Alexandria",
            )
            skill = await first_service.save_note(
                ObsidianSaveNote(
                    title="Browser Verification Skill",
                    body=(
                        "# Browser Verification Skill\n\n"
                        "Use deterministic browser checks and bounded waits."
                    ),
                    alexandria_type=AlexandriaNoteType.SKILL,
                    note_id="skill_browser_verification",
                    project="alexandria-hermes",
                    tags=["skill", "verification"],
                    source="import",
                    frontmatter={
                        "artifact_kind": "skill",
                        "skill_status": "draft",
                    },
                )
            )
            prompt = await first_service.save_note(
                ObsidianSaveNote(
                    title="Release Review Prompt",
                    body=(
                        "# Release Review Prompt\n\n"
                        "Check changelog, tests, and rollback notes before release."
                    ),
                    alexandria_type=AlexandriaNoteType.PROMPT,
                    note_id="prompt_release_review",
                    project="alexandria-hermes",
                    tags=["prompt", "release"],
                    source="import",
                    frontmatter={
                        "artifact_kind": "prompt",
                        "prompt_kind": "template",
                    },
                )
            )
        finally:
            await first_session.close()
            await first_database.shutdown()

        rebuild_database = Database(
            database_url=_database_url(tmp_path / "rebuilt.db"),
            create_schema=True,
        )
        await rebuild_database.initialize()
        rebuild_session = rebuild_database.session()
        try:
            rebuilt_service = ObsidianService(
                repository=SqlAlchemyObsidianIndexRepository(session=rebuild_session),
                vault_path=str(vault_path),
                alexandria_root="Alexandria",
            )
            reindex = await rebuilt_service.reindex()
            memory_hits = await rebuilt_service.search(
                ObsidianSearchQuery(
                    query="canonical memory survives",
                    alexandria_type=AlexandriaNoteType.MEMORY_COMPACT,
                    project="alexandria-hermes",
                ),
                refresh=False,
            )
            skill_hits = await rebuilt_service.search(
                ObsidianSearchQuery(
                    query="deterministic browser checks",
                    alexandria_type=AlexandriaNoteType.SKILL,
                ),
                refresh=False,
            )
            prompt_hits = await rebuilt_service.search(
                ObsidianSearchQuery(
                    query="rollback notes before release",
                    alexandria_type=AlexandriaNoteType.PROMPT,
                ),
                refresh=False,
            )
            memory_note = await rebuilt_service.read_note_by_path(
                f"Alexandria/Memory Compacts/{compact.id}.md"
            )
            skill_note = await rebuilt_service.read_note(skill.note_id)
            prompt_note = await rebuilt_service.read_note(prompt.note_id)
        finally:
            await rebuild_session.close()
            await rebuild_database.shutdown()

        assert reindex.files_indexed == 3
        assert memory_hits[0].note.note_id == compact.id
        assert skill_hits[0].note.note_id == "skill_browser_verification"
        assert prompt_hits[0].note.note_id == "prompt_release_review"
        assert memory_note.alexandria_type is AlexandriaNoteType.MEMORY_COMPACT
        assert memory_note.body.startswith("# Current Memory Compact")
        assert skill_note.frontmatter["skill_status"] == "draft"
        assert prompt_note.frontmatter["prompt_kind"] == "template"

    anyio.run(scenario)


def test_obsidian_save_existing_default_path_reuses_note_id(tmp_path: Path) -> None:
    """Saving the same generated path twice should update instead of path-conflict."""

    async def scenario() -> None:
        database, session, service = await _service(tmp_path)
        try:
            first = await service.save_note(
                ObsidianSaveNote(
                    title="Repeatable Smoke",
                    body="# Repeatable Smoke\n\nfirst body",
                    alexandria_type=AlexandriaNoteType.JOB_PLAN,
                    tags=["smoke-test"],
                )
            )
            second = await service.save_note(
                ObsidianSaveNote(
                    title="Repeatable Smoke",
                    body="# Repeatable Smoke\n\nsecond body",
                    alexandria_type=AlexandriaNoteType.JOB_PLAN,
                    tags=["smoke-test"],
                )
            )
        finally:
            await session.close()
            await database.shutdown()

        assert second.note_id == first.note_id
        assert second.relative_path == first.relative_path
        assert "second body" in second.body

    anyio.run(scenario)


def test_obsidian_read_rejects_indexed_note_missing_frontmatter(tmp_path: Path) -> None:
    """Read should not hide source Markdown corruption behind SQLite cache data."""

    async def scenario() -> None:
        database, session, service = await _service(tmp_path)
        try:
            saved = await service.save_note(
                ObsidianSaveNote(
                    title="Canonical Note",
                    body="# Canonical Note\n\nOriginal source.",
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="ctx_canonical",
                )
            )
            note_path = tmp_path / "vault" / saved.relative_path
            note_path.write_text(
                "# Canonical Note\n\nfrontmatter removed", encoding="utf-8"
            )
            try:
                await service.read_note("ctx_canonical")
            except ObsidianValidationError as exc:
                message = str(exc)
            else:
                message = ""
        finally:
            await session.close()
            await database.shutdown()

        assert "missing Alexandria frontmatter" in message

    anyio.run(scenario)


def test_obsidian_save_note_redacts_secret_like_frontmatter_values(
    tmp_path: Path,
) -> None:
    """Secret-like frontmatter strings should not be written raw."""

    async def scenario() -> None:
        database, session, service = await _service(tmp_path)
        try:
            saved = await service.save_note(
                ObsidianSaveNote(
                    title="Frontmatter Redaction",
                    body="# Frontmatter Redaction\n\nSafe body.",
                    alexandria_type=AlexandriaNoteType.PROMPT,
                    note_id="prompt_frontmatter_redaction",
                    frontmatter={
                        "prompt_kind": "template",
                        "metadata": {
                            "api_key": "sk-" + ("x" * 60),
                        },
                    },
                )
            )
        finally:
            await session.close()
            await database.shutdown()

        note_text = (tmp_path / "vault" / saved.relative_path).read_text(
            encoding="utf-8"
        )
        assert "sk-" + ("x" * 60) not in note_text
        assert "<REDACTED_LONG_VALUE>" in note_text
        assert "potential secret-like content was redacted" in note_text

    anyio.run(scenario)


def test_obsidian_librarian_ask_delegates_with_auto_provider(
    tmp_path: Path,
) -> None:
    """Delegate requests should use the configured delegate service without caller ids."""

    async def scenario() -> tuple[str, str | None, str | None, bool, str | None]:
        database = Database(
            database_url=_database_url(tmp_path / "obsidian.db"), create_schema=True
        )
        await database.initialize()
        session = database.session()
        delegate = _RecordingDelegateService()
        service = ObsidianService(
            repository=SqlAlchemyObsidianIndexRepository(session=session),
            vault_path=str(tmp_path / "vault"),
            alexandria_root="Alexandria",
            delegate_service=delegate,
        )
        try:
            note = await service.save_note(
                ObsidianSaveNote(
                    title="Delegate Source",
                    body="# Delegate Source\n\nObsidian delegate source marker.",
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="ctx_delegate_source",
                    project="alexandria-hermes",
                )
            )
            response = await service.ask_librarian(
                ObsidianLibrarianAsk(
                    query="Obsidian delegate source marker",
                    active_note_path=note.relative_path,
                    project="alexandria-hermes",
                    delegate_to_librarian=True,
                )
            )
        finally:
            await session.close()
            await database.shutdown()
        return (
            str(response["delegate_status"]),
            response["provider_id"]
            if isinstance(response["provider_id"], str)
            else None,
            response["profile_id"] if isinstance(response["profile_id"], str) else None,
            "provider-backed compact guidance" in str(response["answer_markdown"]),
            None if delegate.command is None else delegate.command.provider_id,
        )

    status, provider_id, profile_id, summary_added, requested_provider = anyio.run(
        scenario
    )

    assert status == "COMPLETED"
    assert provider_id == "auto-provider"
    assert profile_id == "auto-profile"
    assert summary_added is True
    assert requested_provider is None


def test_obsidian_librarian_ask_fails_when_active_note_path_cannot_be_read(
    tmp_path: Path,
) -> None:
    """Caller-supplied active_note_path should fail clearly when unreadable."""

    async def scenario() -> str:
        database, session, service = await _service(tmp_path)
        try:
            try:
                await service.ask_librarian(
                    ObsidianLibrarianAsk(
                        query="Use the active inventory note.",
                        active_note_path="Alexandria/Contexts/Missing.md",
                    )
                )
            except ObsidianValidationError as exc:
                return str(exc)
            return ""
        finally:
            await session.close()
            await database.shutdown()

    message = anyio.run(scenario)

    assert message == "active_note_read_failed: Alexandria/Contexts/Missing.md"


def test_obsidian_librarian_ask_includes_selection_in_delegate_brief(
    tmp_path: Path,
) -> None:
    """Selection should remain explicit context for provider-backed delegation."""

    async def scenario() -> tuple[str, str, str]:
        database = Database(
            database_url=_database_url(tmp_path / "obsidian.db"), create_schema=True
        )
        await database.initialize()
        session = database.session()
        delegate = _RecordingDelegateService()
        service = ObsidianService(
            repository=SqlAlchemyObsidianIndexRepository(session=session),
            vault_path=str(tmp_path / "vault"),
            alexandria_root="Alexandria",
            delegate_service=delegate,
        )
        selection = (
            "Inventory update:\n- Contexts/Projects/Loose A.md -> project/Loose A.md"
        )
        try:
            response = await service.ask_librarian(
                ObsidianLibrarianAsk(
                    query="Plan the inventory move.",
                    selection=selection,
                    project="alexandria-hermes",
                    delegate_to_librarian=True,
                )
            )
        finally:
            await session.close()
            await database.shutdown()
        assert delegate.command is not None
        return (
            str(response["input_context"]),
            delegate.command.prompt,
            delegate.command.librarian_brief or "",
        )

    context, prompt, brief = anyio.run(scenario)

    assert "selection_status': 'ingested'" in context
    assert "Answer the user's question" in prompt
    assert "Inventory update" in prompt
    assert "Inventory update" in brief
    assert "Do not review a prewritten answer" in brief
    assert "selection_status: ingested" in brief


def test_obsidian_librarian_ask_uses_active_note_as_source(tmp_path: Path) -> None:
    """Active note context should be returned as a source even for broad questions."""

    async def scenario() -> None:
        database, session, service = await _service(tmp_path)
        try:
            note = await service.save_note(
                ObsidianSaveNote(
                    title="Active Context",
                    body="# Active Context\n\nMarkdown is canonical.",
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="ctx_active_source",
                    project="alexandria-hermes",
                )
            )
            response = await service.ask_librarian(
                ObsidianLibrarianAsk(
                    query="이 노트에서 확인한 원칙은?",
                    active_note_path=note.relative_path,
                    project="alexandria-hermes",
                )
            )
        finally:
            await session.close()
            await database.shutdown()

        assert response["source_refs"] == [
            {
                "id": "ctx_active_source",
                "alexandria_type": "context",
                "path": note.relative_path,
                "title": "Active Context",
                "wikilink": "[[Alexandria/Contexts/Projects/Active Context]]",
            }
        ]

    anyio.run(scenario)


def test_obsidian_librarian_source_miss_is_not_reported_as_no_related_notes(
    tmp_path: Path,
) -> None:
    """Search misses should report insufficient inventory, not true absence."""

    async def scenario() -> tuple[str, str, list[str]]:
        database, session, service = await _service(tmp_path)
        try:
            response = await service.ask_librarian(
                ObsidianLibrarianAsk(
                    query="nonexistent dogfood inventory marker",
                    project="alexandria-hermes",
                )
            )
        finally:
            await session.close()
            await database.shutdown()
        context = response["input_context"]
        assert isinstance(context, dict)
        warnings = context.get("warnings")
        assert isinstance(warnings, list)
        return (
            str(response["context_status"]),
            str(response["answer_markdown"]),
            [str(item) for item in warnings],
        )

    status, answer, warnings = anyio.run(scenario)

    assert status == "insufficient_inventory"
    assert "관련 note 없음" not in answer
    assert "Alexandria Librarian Context Packet" in answer
    assert "## Retrieved Sources\n- none" in answer
    assert warnings == [
        "source_miss_is_not_no_related_notes_without_inventory_verification"
    ]


def test_obsidian_librarian_ask_respects_max_source_refs(tmp_path: Path) -> None:
    """Whole-vault librarian asks should be able to retrieve more than the old tiny UI limit."""

    async def scenario() -> None:
        database, session, service = await _service(tmp_path)
        try:
            for index in range(6):
                await service.save_note(
                    ObsidianSaveNote(
                        title=f"Vault Scope Source {index}",
                        body="# Vault Scope\n\nwhole vault librarian scope marker",
                        alexandria_type=AlexandriaNoteType.CONTEXT,
                        note_id=f"ctx_vault_scope_{index}",
                        project="alexandria-hermes",
                    )
                )
            response = await service.ask_librarian(
                ObsidianLibrarianAsk(
                    query="whole vault librarian scope marker",
                    project="alexandria-hermes",
                    max_source_refs=4,
                )
            )
        finally:
            await session.close()
            await database.shutdown()

        assert len(response["source_refs"]) == 4

    anyio.run(scenario)


def test_obsidian_librarian_vault_inventory_and_path_search(
    tmp_path: Path,
) -> None:
    """Vault operation inventory should read managed notes without FTS dependency."""

    async def scenario() -> tuple[list[str], list[str]]:
        database, session, service = await _service(tmp_path)
        try:
            await service.save_note(
                ObsidianSaveNote(
                    title="Loose Project Context",
                    body="# Loose Project Context\n\nInventory marker.",
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="ctx_loose_project_context",
                    relative_path=(
                        "Alexandria/Contexts/Projects/Loose Project Context.md"
                    ),
                    project="alexandria-hermes",
                )
            )
            inventory = await service.inventory_vault(
                ObsidianVaultInventoryRequest(scope_path="Alexandria/Contexts/Projects")
            )
            matches = await service.search_vault_paths(
                query="Loose Project",
                scope_path="Alexandria/Contexts/Projects",
            )
        finally:
            await session.close()
            await database.shutdown()
        return (
            [item.relative_path for item in inventory],
            [item.note_id for item in matches],
        )

    paths, matches = anyio.run(scenario)

    assert paths == ["Alexandria/Contexts/Projects/Loose Project Context.md"]
    assert matches == ["ctx_loose_project_context"]


def test_obsidian_librarian_vault_move_plan_blocks_overwrite(
    tmp_path: Path,
) -> None:
    """Dry-run move planning should reject overwrites before mutation."""

    async def scenario() -> tuple[str, str, bool]:
        database, session, service = await _service(tmp_path)
        try:
            source = await service.save_note(
                ObsidianSaveNote(
                    title="Move Source",
                    body="# Move Source\n\nSource body.",
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="ctx_move_source",
                    relative_path="Alexandria/Contexts/Projects/Move Source.md",
                )
            )
            destination = await service.save_note(
                ObsidianSaveNote(
                    title="Move Destination",
                    body="# Move Destination\n\nDestination body.",
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="ctx_move_destination",
                    relative_path=(
                        "Alexandria/Contexts/Projects/organized/Move Source.md"
                    ),
                )
            )
            plan = await service.plan_vault_moves(
                ObsidianVaultMovePlanRequest(
                    moves=[
                        ObsidianVaultMoveRequest(
                            source_path=source.relative_path,
                            destination_path=destination.relative_path,
                            reason="organize loose note",
                        )
                    ]
                )
            )
            source_exists = (tmp_path / "vault" / source.relative_path).exists()
        finally:
            await session.close()
            await database.shutdown()
        return plan.status, plan.skipped[0].reason, source_exists

    status, skip_reason, source_exists = anyio.run(scenario)

    assert status == "blocked"
    assert skip_reason == "destination_exists"
    assert source_exists is True


def test_obsidian_librarian_vault_apply_moves_writes_reports_and_reindexes(
    tmp_path: Path,
) -> None:
    """Applying moves should preserve notes, write reports, and rebuild the index."""

    async def scenario() -> tuple[str, str, str, bool, bool, bool, int]:
        database, session, service = await _service(tmp_path)
        try:
            source = await service.save_note(
                ObsidianSaveNote(
                    title="Apply Source",
                    body="# Apply Source\n\nverification move marker.",
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="ctx_apply_source",
                    relative_path="Alexandria/Contexts/Projects/Apply Source.md",
                    project="alexandria-hermes",
                )
            )
            report = await service.apply_vault_moves(
                ObsidianVaultMoveApplyRequest(
                    moves=[
                        ObsidianVaultMoveRequest(
                            source_path=source.relative_path,
                            destination_path=(
                                "Alexandria/Contexts/Projects/organized/Apply Source.md"
                            ),
                            reason="organize loose note",
                        )
                    ],
                    report_path="Alexandria/_Ops/Librarian/Reports/apply-source-report",
                    verification_query="verification move marker",
                )
            )
            moved_note = await service.read_note_by_path(
                report.moved[0].destination_path
            )
            report_json = loads_json(
                (tmp_path / "vault" / report.report_json_path).read_bytes()
            )
        finally:
            await session.close()
            await database.shutdown()
        assert isinstance(report_json, dict)
        return (
            report.status,
            moved_note.note_id,
            report.verification.reindex_status,
            report.hard_delete_performed,
            (tmp_path / "vault" / source.relative_path).exists(),
            (tmp_path / "vault" / report.report_markdown_path).exists(),
            int(report_json["verification"]["verification_hits"]),
        )

    (
        status,
        note_id,
        reindex_status,
        hard_delete_performed,
        source_exists,
        markdown_report_exists,
        verification_hits,
    ) = anyio.run(scenario)

    assert status == "succeeded"
    assert note_id == "ctx_apply_source"
    assert reindex_status == "succeeded"
    assert hard_delete_performed is False
    assert source_exists is False
    assert markdown_report_exists is True
    assert verification_hits == 1


def test_obsidian_librarian_vault_apply_preflights_report_before_moves(
    tmp_path: Path,
) -> None:
    """Report destination conflicts should fail before any vault mutation."""

    async def scenario() -> tuple[bool, bool]:
        database, session, service = await _service(tmp_path)
        try:
            source = await service.save_note(
                ObsidianSaveNote(
                    title="Preflight Source",
                    body="# Preflight Source\n\nmust stay put.",
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="ctx_preflight_source",
                    relative_path=("Alexandria/Contexts/Projects/Preflight Source.md"),
                )
            )
            report_path = (
                tmp_path
                / "vault"
                / "Alexandria"
                / "_Ops"
                / "Librarian"
                / "Reports"
                / "preflight-report.md"
            )
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text("existing report", encoding="utf-8")

            try:
                await service.apply_vault_moves(
                    ObsidianVaultMoveApplyRequest(
                        moves=[
                            ObsidianVaultMoveRequest(
                                source_path=source.relative_path,
                                destination_path=(
                                    "Alexandria/Contexts/Projects/organized/"
                                    "Preflight Source.md"
                                ),
                                reason="organize loose note",
                            )
                        ],
                        report_path="Alexandria/_Ops/Librarian/Reports/preflight-report",
                    )
                )
            except ObsidianValidationError as exc:
                assert str(exc) == "vault move report destination exists"
            else:
                raise AssertionError("report preflight conflict did not fail")
        finally:
            await session.close()
            await database.shutdown()

        return (
            (tmp_path / "vault" / source.relative_path).exists(),
            (
                tmp_path
                / "vault"
                / "Alexandria/Contexts/Projects/organized/Preflight Source.md"
            ).exists(),
        )

    source_exists, destination_exists = anyio.run(scenario)

    assert source_exists is True
    assert destination_exists is False


def test_obsidian_librarian_job_routes_run_vault_move_and_expose_report(
    tmp_path: Path,
) -> None:
    """Job API should own a fresh session and commit background reindex writes."""

    destination_path = "Alexandria/Contexts/Projects/organized/Async Job Source.md"

    async def prepare() -> tuple[Database, ObsidianLibrarianJobService, str]:
        database = Database(
            database_url=_database_url(tmp_path / "obsidian-job-api.db"),
            create_schema=True,
        )
        await database.initialize()
        config_store = ObsidianVaultConfigStore(
            default_vault_path=str(tmp_path / "vault"),
            default_alexandria_root="Alexandria",
            config_path=None,
        )
        async with database.session_factory()() as session:
            service = ObsidianService(
                repository=SqlAlchemyObsidianIndexRepository(session=session),
                vault_config_store=config_store,
            )
            source = await service.save_note(
                ObsidianSaveNote(
                    title="Async Job Source",
                    body="# Async Job Source\n\nasync job marker.",
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="ctx_async_job_source",
                    relative_path=("Alexandria/Contexts/Projects/Async Job Source.md"),
                    project="alexandria-hermes",
                )
            )
            await session.commit()
        job_service = ObsidianLibrarianJobService(
            database=database,
            vault_config_store=config_store,
        )
        return database, job_service, source.relative_path

    async def destination_committed(database: Database) -> bool:
        async with database.session_factory()() as session:
            note = await session.scalar(
                select(ObsidianFileORM).where(
                    ObsidianFileORM.relative_path == destination_path
                )
            )
        return (
            note is not None and note.index_status == ObsidianIndexStatus.INDEXED.value
        )

    database, job_service, source_path = anyio.run(prepare)
    try:
        with (
            app.state.container.obsidian.providers["job_service"].override(
                providers.Object(job_service)
            ),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            start_response = client.post(
                "/obsidian/librarian/jobs",
                json={
                    "moves": [
                        {
                            "source_path": source_path,
                            "destination_path": destination_path,
                            "reason": "organize loose note",
                        }
                    ],
                    "report_path": (
                        "Alexandria/_Ops/Librarian/Reports/async-job-source-report"
                    ),
                    "verification_query": "async job marker",
                },
            )
            job_id = start_response.json()["job_id"]
            status_response = client.get(f"/obsidian/librarian/jobs/{job_id}")
            report_response = client.get(f"/obsidian/librarian/jobs/{job_id}/report")
        committed = anyio.run(destination_committed, database)
    finally:
        anyio.run(database.shutdown)

    assert start_response.status_code == 202
    assert start_response.json()["status"] == ObsidianLibrarianJobStatus.PENDING.value
    assert status_response.status_code == 200
    assert (
        status_response.json()["status"] == ObsidianLibrarianJobStatus.SUCCEEDED.value
    )
    assert status_response.json()["result_available"] is True
    assert report_response.status_code == 200
    assert report_response.json()["status"] == "succeeded"
    assert report_response.json()["verification"]["verification_hits"] == 1
    assert (tmp_path / "vault" / destination_path).exists()
    assert committed is True


def test_obsidian_reindex_accepts_legacy_project_context_type(
    tmp_path: Path,
) -> None:
    """Legacy project-context notes should remain searchable Alexandria sources."""

    async def scenario() -> None:
        database, session, service = await _service(tmp_path)
        try:
            note_path = (
                tmp_path
                / "vault"
                / "Alexandria"
                / "Contexts"
                / "Project Context"
                / "Legacy Project Context.md"
            )
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text(
                "\n".join(
                    [
                        "---",
                        "id: ctx_legacy_project_context",
                        "title: Legacy Project Context",
                        "type: project-context",
                        "project: omx-agent-adapter",
                        "tags:",
                        "  - command-catalog",
                        "---",
                        "",
                        "# Legacy Project Context",
                        "",
                        "command catalog consolidation durable source",
                    ]
                ),
                encoding="utf-8",
            )

            result = await service.reindex()
            response = await service.search(
                ObsidianSearchQuery(
                    query="command catalog consolidation",
                    project="omx-agent-adapter",
                )
            )
        finally:
            await session.close()
            await database.shutdown()

        assert result.errors == []
        assert [hit.note.note_id for hit in response] == ["ctx_legacy_project_context"]
        assert response[0].note.alexandria_type is AlexandriaNoteType.CONTEXT
        assert response[0].note.frontmatter["alexandria_type"] == "context"

    anyio.run(scenario)


def test_obsidian_librarian_ask_recovers_multi_topic_sources_without_chat_echo(
    tmp_path: Path,
) -> None:
    """Long recall questions should retrieve source notes, not prior failed chats."""

    async def scenario() -> list[dict[str, object]]:
        database, session, service = await _service(tmp_path)
        try:
            legacy_path = (
                tmp_path
                / "vault"
                / "Alexandria"
                / "Contexts"
                / "Project Context"
                / "Command Catalog Consolidation.md"
            )
            legacy_path.parent.mkdir(parents=True, exist_ok=True)
            legacy_path.write_text(
                "\n".join(
                    [
                        "---",
                        "id: ctx_command_catalog_consolidation",
                        "title: Command Catalog Consolidation",
                        "type: project-context",
                        "project: omx-agent-adapter",
                        "tags:",
                        "  - command-catalog",
                        "---",
                        "",
                        "# Command Catalog Consolidation",
                        "",
                        "command catalog consolidation keeps eight lifecycle commands.",
                        "adapter-ops is a maintenance namespace, not public catalog.",
                    ]
                ),
                encoding="utf-8",
            )
            await service.save_note(
                ObsidianSaveNote(
                    title="Company Run Macro",
                    body=(
                        "# Company Run Macro\n\n"
                        "company-run macro orchestration uses Alexandria MCP usage "
                        "for memory recall and librarian queries."
                    ),
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="ctx_company_run_macro",
                    project="omx-agent-adapter",
                )
            )
            await service.save_note(
                ObsidianSaveNote(
                    title="Failed Librarian Chat",
                    body=(
                        "# Librarian Chat\n\n"
                        "Recover prior intent for omx-agent-adapter command catalog "
                        "consolidation, company-run macro orchestration, prompt/ "
                        "structure, adapter-ops exclusion, and Alexandria MCP usage "
                        "points. Return only concrete prior decisions and artifact "
                        "locations.\n\nNo related Alexandria note found."
                    ),
                    alexandria_type=AlexandriaNoteType.LIBRARIAN_CHAT,
                    note_id="librarian_chat_failed_echo",
                    project="omx-agent-adapter",
                )
            )
            await service.reindex()
            response = await service.ask_librarian(
                ObsidianLibrarianAsk(
                    query=(
                        "Recover prior intent for omx-agent-adapter command catalog "
                        "consolidation, company-run macro orchestration, prompt/ "
                        "structure, adapter-ops exclusion, and Alexandria MCP usage "
                        "points. Return only concrete prior decisions and artifact "
                        "locations."
                    ),
                    project="omx-agent-adapter",
                    max_source_refs=5,
                )
            )
        finally:
            await session.close()
            await database.shutdown()

        source_refs = response["source_refs"]
        assert isinstance(source_refs, list)
        return source_refs

    refs = anyio.run(scenario)

    assert [ref["id"] for ref in refs] == [
        "ctx_command_catalog_consolidation",
        "ctx_company_run_macro",
    ]
    assert all(ref["alexandria_type"] == "context" for ref in refs)


def test_obsidian_librarian_ask_can_save_transcript(tmp_path: Path) -> None:
    """The Obsidian librarian adapter should return sources and save transcript notes."""

    async def scenario() -> None:
        database, session, service = await _service(tmp_path)
        try:
            await service.save_note(
                ObsidianSaveNote(
                    title="Obsidian Storage Decision",
                    body="# Decision\n\nObsidian is canonical storage.",
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="ctx_obsidian_storage",
                    tags=["obsidian"],
                    project="alexandria-hermes",
                )
            )
            response = await service.ask_librarian(
                ObsidianLibrarianAsk(
                    query="canonical storage",
                    project="alexandria-hermes",
                    save_transcript=True,
                )
            )
        finally:
            await session.close()
            await database.shutdown()

        transcript_path = response["transcript_path"]
        assert isinstance(transcript_path, str)
        assert transcript_path.startswith("Alexandria/_Ops/Librarian/Chats/")
        assert response["source_refs"] == [
            {
                "id": "ctx_obsidian_storage",
                "alexandria_type": "context",
                "path": "Alexandria/Contexts/Projects/Obsidian Storage Decision.md",
                "title": "Obsidian Storage Decision",
                "wikilink": "[[Alexandria/Contexts/Projects/Obsidian Storage Decision]]",
            }
        ]

    anyio.run(scenario)
