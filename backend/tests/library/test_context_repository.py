"""Behavior tests for Context Vault repository contracts."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import anyio
import pytest
from app.memory.application.context_service import ContextService
from app.memory.domain.event_enum.context_enums import (
    ContextKind,
    ContextSourceType,
    ContextStorageStatus,
    RagStrategy,
)
from app.memory.infrastructure.repositories.context_repository import (
    SqlAlchemyContextRepository,
)
from app.shared.exceptions import NotFoundError, ValidationError
from app.shared.infrastructure.database import Database


def _handoff_content(extra: str = "") -> str:
    return f"""# Sprint Handoff

## Summary
Context retrieval uses local searchable memory.

## Current State
- Repository stores chunks and FTS rows.
- Hybrid search degrades when vector is unavailable.

## Next Actions
1. Expose the API.

## Restore Prompt
Continue implementing Alexandria context recall.

{extra}
"""


@asynccontextmanager
async def _temporary_database(path: Path) -> AsyncIterator[Database]:
    database = Database(database_url=f"sqlite+aiosqlite:///{path}", create_schema=True)
    await database.initialize()
    try:
        yield database
    finally:
        await database.shutdown()


def test_context_repository_saves_searches_accesses_and_archives_contexts(
    tmp_path: Path,
) -> None:
    """Context Vault should preserve rows, chunks, FTS recall, access metadata, and archives."""

    async def scenario() -> None:
        async with (
            _temporary_database(tmp_path / "contexts.db") as database,
            database.session() as session,
        ):
            repository = SqlAlchemyContextRepository(session=session)
            service = ContextService(repository=repository)

            saved = await service.save(
                kind=ContextKind.HANDOFF,
                title="Sprint handoff",
                summary="Context retrieval uses local searchable memory.",
                content=_handoff_content(),
                project="alexandria-hermes",
                source_agent="Hermes",
                tags=["handoff", "rag"],
            )
            await session.commit()

            listed, total = await service.list_contexts(project="alexandria-hermes")
            chunks = await service.chunks(saved.id)
            pack = await service.search(query="local searchable memory", limit=3)
            accessed = await service.access(saved.id)
            archived = await service.archive(saved.id)
            await session.commit()
            after_archive = await service.search(
                query="local searchable memory", limit=3
            )

        assert total == 1
        assert [item.id for item in listed] == [saved.id]
        assert len(chunks) >= 1
        assert saved.id in {match.context.id for match in pack.matches}
        assert saved.source_type is ContextSourceType.AGENT
        assert "Alexandria Context Pack" in pack.context_pack
        assert accessed.access_count == 1
        assert accessed.last_accessed_at is not None
        assert archived.is_archived is True
        assert after_archive.matches == []

    anyio.run(scenario)


def test_context_repository_raises_not_found_when_archive_target_is_missing(
    tmp_path: Path,
) -> None:
    """Archive-first behavior should still report missing context ids explicitly."""

    async def scenario() -> None:
        async with (
            _temporary_database(tmp_path / "missing-context.db") as database,
            database.session() as session,
        ):
            service = ContextService(
                repository=SqlAlchemyContextRepository(session=session)
            )
            missing_id = "00000000-0000-4000-8000-000000000000"

            with pytest.raises(NotFoundError, match=f"Context not found: {missing_id}"):
                await service.archive(missing_id)

    anyio.run(scenario)


def test_context_service_blocks_private_key_contexts_before_persistence(
    tmp_path: Path,
) -> None:
    """High-risk secret content must not be saved raw."""

    async def scenario() -> None:
        async with (
            _temporary_database(tmp_path / "secret-context.db") as database,
            database.session() as session,
        ):
            service = ContextService(
                repository=SqlAlchemyContextRepository(session=session)
            )

            with pytest.raises(ValidationError, match="high-risk secret"):
                await service.save(
                    kind=ContextKind.HANDOFF,
                    title="Unsafe handoff",
                    summary="Contains a private key.",
                    content=_handoff_content(
                        "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----"
                    ),
                )

            listed, total = await service.list_contexts()

        assert total == 0
        assert listed == []

    anyio.run(scenario)


def test_context_service_redacts_token_like_values_before_persistence(
    tmp_path: Path,
) -> None:
    """Token-like assignments should be masked in stored content."""

    async def scenario() -> None:
        async with (
            _temporary_database(tmp_path / "redacted-context.db") as database,
            database.session() as session,
        ):
            service = ContextService(
                repository=SqlAlchemyContextRepository(session=session)
            )
            saved = await service.save(
                kind=ContextKind.HANDOFF,
                title="Redacted handoff",
                summary="Token should be masked.",
                content=_handoff_content("api_key=abc123456789999999"),
            )
            await session.commit()
            stored = await service.get(saved.id)

        assert stored.status is ContextStorageStatus.REDACTED_AND_SAVED
        assert "abc123456789999999" not in stored.content
        assert "api_key=<REDACTED>" in stored.content

    anyio.run(scenario)


def test_context_rag_defaults_to_fts_only_when_vector_provider_is_degraded(
    tmp_path: Path,
) -> None:
    """Hybrid retrieval should continue with FTS when vector health is unavailable."""

    async def scenario() -> None:
        async with (
            _temporary_database(tmp_path / "rag-fallback.db") as database,
            database.session() as session,
        ):
            service = ContextService(
                repository=SqlAlchemyContextRepository(session=session)
            )
            await service.save(
                kind=ContextKind.RESEARCH,
                title="sqlite vec fallback",
                summary="FTS remains available when vectors degrade.",
                content="""# Research

## Summary
FTS remains available when vectors degrade.

## Evidence
sqlite-vec may not load in CI.
""",
                tags=["rag"],
            )
            await session.commit()

            health = service.rag_health()
            pack = await service.search(
                query="vectors degrade",
                strategy=RagStrategy.HYBRID,
                limit=2,
            )
            vector_only_pack = await service.search(
                query="vectors degrade",
                strategy=RagStrategy.VECTOR_ONLY,
                limit=2,
            )

        assert health.default_strategy is RagStrategy.FTS_ONLY
        assert health.vector.value == "DISABLED"
        assert pack.effective_strategy is RagStrategy.FTS_ONLY
        assert vector_only_pack.effective_strategy is RagStrategy.FTS_ONLY
        assert pack.matches
        assert any("FTS_ONLY" in warning for warning in pack.warnings)
        assert any("FTS_ONLY" in warning for warning in vector_only_pack.warnings)

    anyio.run(scenario)


def test_context_list_filters_tags_by_exact_membership(tmp_path: Path) -> None:
    """Tag filtering should not match substrings inside other tag names."""

    async def scenario() -> None:
        async with (
            _temporary_database(tmp_path / "tags.db") as database,
            database.session() as session,
        ):
            service = ContextService(
                repository=SqlAlchemyContextRepository(session=session)
            )
            exact = await service.save(
                kind=ContextKind.HANDOFF,
                title="API handoff",
                summary="API tag should match exactly.",
                content=_handoff_content("API context."),
                tags=["api"],
                source_type=ContextSourceType.IMPORTED,
            )
            await service.save(
                kind=ContextKind.HANDOFF,
                title="Capistrano handoff",
                summary="Substring should not match.",
                content=_handoff_content("Deployment context."),
                tags=["capistrano"],
            )
            await session.commit()

            listed, total = await service.list_contexts(tag="api")

        assert total == 1
        assert [item.id for item in listed] == [exact.id]

    anyio.run(scenario)
