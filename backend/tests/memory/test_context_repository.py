"""Behavior tests for Context Vault repository contracts."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from threading import Event

import anyio
import pytest
from app.memory.application.context_service import ContextService
from app.memory.domain.entities.context_read_models import ContextPack
from app.memory.domain.event_enum.context_enums import (
    ContextAccessActorType,
    ContextAccessMethod,
    ContextKind,
    ContextSourceType,
    RagHealthState,
    RagStrategy,
)
from app.memory.infrastructure.models.context_models import ContextChunkORM, ContextORM
from app.memory.infrastructure.repositories.context_repository import (
    SqlAlchemyContextRepository,
)
from tests.memory.context_seed import seed_context
from app.retrieval.application.embedding_provider import EmbeddingProvider
from app.shared.exceptions import (
    MemoryContextNotFoundError,
)
from app.shared.infrastructure.database import Database
from sqlalchemy import select


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


class KeywordEmbeddingProvider(EmbeddingProvider):
    """Deterministic provider that maps test keywords to stable vectors."""

    @property
    def provider_name(self) -> str:
        return "KEYWORD_TEST"

    @property
    def model_name(self) -> str:
        return "keyword-test-model"

    @property
    def dimensions(self) -> int:
        return 3

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        if "semantic-target" in text or "query-alias" in text:
            return [1.0, 0.0, 0.0]
        if "distractor" in text:
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]


class MeanPoolingUpgradeEmbeddingProvider(EmbeddingProvider):
    """Provider stand-in for same model/dimensions after a pooling upgrade."""

    @property
    def provider_name(self) -> str:
        return "KEYWORD_TEST"

    @property
    def model_name(self) -> str:
        return "keyword-test-model"

    @property
    def dimensions(self) -> int:
        return 3

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [[0.0, 1.0, 0.0] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.0, 1.0, 0.0]


class BlockingEmbeddingProvider(EmbeddingProvider):
    """Embedding provider fake that blocks until an async task releases it."""

    def __init__(self) -> None:
        self.documents_started = Event()
        self.query_started = Event()
        self._documents_release = Event()
        self._query_release = Event()
        self.documents_released_by_async_task = False
        self.query_released_by_async_task = False

    @property
    def provider_name(self) -> str:
        return "BLOCKING_TEST"

    @property
    def model_name(self) -> str:
        return "keyword-test-model"

    @property
    def dimensions(self) -> int:
        return 3

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        self.documents_started.set()
        self.documents_released_by_async_task = self._documents_release.wait(
            timeout=0.2
        )
        return [[1.0, 0.0, 0.0] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        _ = text
        self.query_started.set()
        self.query_released_by_async_task = self._query_release.wait(timeout=0.2)
        return [1.0, 0.0, 0.0]

    def release_documents(self) -> None:
        """Release the blocked document embedding call."""
        self._documents_release.set()

    def release_query(self) -> None:
        """Release the blocked query embedding call."""
        self._query_release.set()


@asynccontextmanager
async def _temporary_database(path: Path) -> AsyncIterator[Database]:
    database = Database(database_url=f"sqlite+aiosqlite:///{path}", create_schema=True)
    await database.initialize()
    try:
        yield database
    finally:
        await database.shutdown()


def test_context_repository_searches_accesses_and_archives_seeded_contexts(
    tmp_path: Path,
) -> None:
    """Context Vault should recall seeded rows and preserve access/archive behavior."""

    async def scenario() -> None:
        async with (
            _temporary_database(tmp_path / "contexts.db") as database,
            database.session() as session,
        ):
            repository = SqlAlchemyContextRepository(session=session)
            service = ContextService(repository=repository)

            saved = await seed_context(
                session,
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
            accessed = await service.access(
                saved.id,
                actor_name="Alexandria UI",
                actor_type=ContextAccessActorType.UI,
                access_method=ContextAccessMethod.DETAIL_VIEW,
                source_surface="context-detail",
            )
            await anyio.sleep(0.001)
            await service.access(
                saved.id,
                actor_name="Hermes",
                actor_type=ContextAccessActorType.AGENT,
                access_method=ContextAccessMethod.RECALL,
                source_surface="memory-recall",
            )
            after_second_access = await service.get(saved.id)
            recent_events = await service.access_events(saved.id, limit=5)
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
        assert after_second_access.access_count == 2
        assert [event.actor_name for event in recent_events] == [
            "Hermes",
            "Alexandria UI",
        ]
        assert recent_events[0].access_method is ContextAccessMethod.RECALL
        assert recent_events[1].source_surface == "context-detail"
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

            with pytest.raises(
                MemoryContextNotFoundError, match=f"Context not found: {missing_id}"
            ):
                await service.archive(missing_id)

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
            await seed_context(
                session,
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


def test_context_vector_search_returns_semantic_match_when_enabled(
    tmp_path: Path,
) -> None:
    """Vector retrieval should use stored embeddings when vector dependencies are healthy."""

    async def scenario() -> None:
        async with (
            _temporary_database(tmp_path / "rag-vector.db") as database,
            database.session() as session,
        ):
            service = ContextService(
                repository=SqlAlchemyContextRepository(session=session),
                embedding_provider=KeywordEmbeddingProvider(),
                vector_retrieval_enabled=True,
            )
            target = await seed_context(
                session,
                kind=ContextKind.RESEARCH,
                title="Semantic target",
                summary="Embedding-only context.",
                content="""# Semantic target

## Summary
Embedding-only context.

## Evidence
semantic-target carries vector meaning only.
""",
                embedding_provider=KeywordEmbeddingProvider(),
            )
            await seed_context(
                session,
                kind=ContextKind.RESEARCH,
                title="Distractor",
                summary="Different embedding.",
                content="""# Distractor

## Summary
Different embedding.

## Evidence
distractor should rank behind the semantic target.
""",
                embedding_provider=KeywordEmbeddingProvider(),
            )
            await session.commit()

            health = service.rag_health()
            vector_pack = await service.search(
                query="query-alias",
                strategy=RagStrategy.VECTOR_ONLY,
                limit=1,
            )
            hybrid_pack = await service.search(
                query="query-alias",
                strategy=RagStrategy.HYBRID,
                limit=1,
            )

        assert health.vector is RagHealthState.HEALTHY
        assert health.embedding is RagHealthState.HEALTHY
        assert health.default_strategy is RagStrategy.HYBRID
        assert vector_pack.effective_strategy is RagStrategy.VECTOR_ONLY
        assert hybrid_pack.effective_strategy is RagStrategy.HYBRID
        matched_context_ids = {match.context.id for match in vector_pack.matches}
        assert matched_context_ids == {target.id}
        assert vector_pack.matches[0].fts_score is None
        assert vector_pack.matches[0].vector_score is not None
        assert vector_pack.matches[0].score == vector_pack.matches[0].vector_score
        assert [match.context.id for match in hybrid_pack.matches] == [target.id]
        assert hybrid_pack.matches[0].vector_score is not None

    anyio.run(scenario)


def test_context_vector_search_offloads_blocking_query_embedding_from_event_loop(
    tmp_path: Path,
) -> None:
    """Vector search should not block the event loop while embedding the query."""

    async def scenario() -> None:
        async with (
            _temporary_database(
                tmp_path / "rag-query-embedding-offload.db"
            ) as database,
            database.session() as session,
        ):
            repository = SqlAlchemyContextRepository(session=session)
            target = await seed_context(
                session,
                kind=ContextKind.RESEARCH,
                title="Semantic target",
                summary="Stored with keyword embeddings.",
                content="""# Semantic target

## Summary
semantic-target carries vector meaning.
""",
                embedding_provider=KeywordEmbeddingProvider(),
            )
            await session.commit()

            provider = BlockingEmbeddingProvider()
            search_service = ContextService(
                repository=repository,
                embedding_provider=provider,
                vector_retrieval_enabled=True,
            )
            packs: list[ContextPack] = []

            async def search_contexts() -> None:
                pack = await search_service.search(
                    query="query-alias",
                    strategy=RagStrategy.VECTOR_ONLY,
                    limit=1,
                )
                packs.append(pack)

            async def release_when_query_embedding_starts() -> None:
                while not provider.query_started.is_set():
                    await anyio.sleep(0)
                provider.release_query()

            with anyio.fail_after(1):
                async with anyio.create_task_group() as task_group:
                    task_group.start_soon(search_contexts)
                    task_group.start_soon(release_when_query_embedding_starts)

        assert provider.query_released_by_async_task is True
        assert [[match.context.id for match in pack.matches] for pack in packs] == [
            [target.id]
        ]

    anyio.run(scenario)


def test_context_vector_search_binds_filter_values_when_project_looks_like_sql(
    tmp_path: Path,
) -> None:
    """Vector retrieval should treat SQL-looking filter values as data."""

    async def scenario() -> None:
        async with (
            _temporary_database(tmp_path / "rag-vector-injection.db") as database,
            database.session() as session,
        ):
            service = ContextService(
                repository=SqlAlchemyContextRepository(session=session),
                embedding_provider=KeywordEmbeddingProvider(),
                vector_retrieval_enabled=True,
            )
            sql_like_project = "alexandria' OR 1=1 --"
            target = await seed_context(
                session,
                kind=ContextKind.RESEARCH,
                title="Bound parameter target",
                summary="semantic-target belongs to the SQL-looking project.",
                content="""# Bound parameter target

## Summary
semantic-target belongs to the SQL-looking project.
""",
                project=sql_like_project,
                embedding_provider=KeywordEmbeddingProvider(),
            )
            await seed_context(
                session,
                kind=ContextKind.RESEARCH,
                title="Other semantic target",
                summary="semantic-target belongs to another project.",
                content="""# Other semantic target

## Summary
semantic-target belongs to another project.
""",
                project="other-project",
                embedding_provider=KeywordEmbeddingProvider(),
            )
            await session.commit()

            vector_pack = await service.search(
                query="query-alias",
                strategy=RagStrategy.VECTOR_ONLY,
                project=sql_like_project,
                limit=5,
            )

        matched_context_ids = {match.context.id for match in vector_pack.matches}
        assert matched_context_ids == {target.id}

    anyio.run(scenario)


def test_context_fts_search_binds_filter_values_when_project_looks_like_sql(
    tmp_path: Path,
) -> None:
    """FTS retrieval should treat SQL-looking filter values as data."""

    async def scenario() -> None:
        async with (
            _temporary_database(tmp_path / "rag-fts-injection.db") as database,
            database.session() as session,
        ):
            service = ContextService(
                repository=SqlAlchemyContextRepository(session=session)
            )
            sql_like_project = "alexandria' OR 1=1 --"
            target = await seed_context(
                session,
                kind=ContextKind.RESEARCH,
                title="FTS bound target",
                summary="sharedmarker belongs to the SQL-looking project.",
                content="""# FTS bound target

## Summary
sharedmarker belongs to the SQL-looking project.
""",
                project=sql_like_project,
            )
            await seed_context(
                session,
                kind=ContextKind.RESEARCH,
                title="FTS other target",
                summary="sharedmarker belongs to another project.",
                content="""# FTS other target

## Summary
sharedmarker belongs to another project.
""",
                project="other-project",
            )
            await session.commit()

            pack = await service.search(
                query="sharedmarker",
                strategy=RagStrategy.FTS_ONLY,
                project=sql_like_project,
                limit=5,
            )

        matched_context_ids = {match.context.id for match in pack.matches}
        assert matched_context_ids == {target.id}

    anyio.run(scenario)


def test_context_fts_search_treats_operator_words_as_literal_terms(
    tmp_path: Path,
) -> None:
    """FTS retrieval should not let reserved query words cause syntax errors."""

    async def scenario() -> None:
        async with (
            _temporary_database(tmp_path / "rag-fts-operators.db") as database,
            database.session() as session,
        ):
            service = ContextService(
                repository=SqlAlchemyContextRepository(session=session)
            )
            target = await seed_context(
                session,
                kind=ContextKind.RESEARCH,
                title="FTS operator target",
                summary="foo OR bar AND NOT secret should be literal terms.",
                content="""# FTS operator target

## Summary
foo OR bar AND NOT secret should be literal terms.
""",
            )
            await session.commit()

            operator_pack = await service.search(
                query="foo OR bar",
                strategy=RagStrategy.FTS_ONLY,
                limit=5,
            )
            not_pack = await service.search(
                query="NOT secret",
                strategy=RagStrategy.FTS_ONLY,
                limit=5,
            )
            punctuation_pack = await service.search(
                query="foo!!! OR??? bar",
                strategy=RagStrategy.FTS_ONLY,
                limit=5,
            )

        expected_ids = {target.id}
        assert {match.context.id for match in operator_pack.matches} == expected_ids
        assert {match.context.id for match in not_pack.matches} == expected_ids
        assert {match.context.id for match in punctuation_pack.matches} == expected_ids

    anyio.run(scenario)


def test_context_reindex_backfills_existing_chunks_for_vector_search(
    tmp_path: Path,
) -> None:
    """Reindex should make pre-vector contexts searchable by embedding."""

    async def scenario() -> None:
        async with (
            _temporary_database(tmp_path / "rag-reindex.db") as database,
            database.session() as session,
        ):
            repository = SqlAlchemyContextRepository(session=session)
            target = await seed_context(
                session,
                kind=ContextKind.RESEARCH,
                title="Old semantic target",
                summary="Saved before vector embedding existed.",
                content="""# Old semantic target

## Summary
Saved before vector embedding existed.

## Evidence
semantic-target was stored without an embedding.
""",
            )
            await session.commit()

            vector_service = ContextService(
                repository=repository,
                embedding_provider=KeywordEmbeddingProvider(),
                vector_retrieval_enabled=True,
            )
            before = await vector_service.search(
                query="query-alias",
                strategy=RagStrategy.VECTOR_ONLY,
                limit=1,
            )
            result = await vector_service.reindex_embeddings(limit=10)
            after = await vector_service.search(
                query="query-alias",
                strategy=RagStrategy.VECTOR_ONLY,
                limit=1,
            )

        assert before.matches == []
        assert result.scanned >= 1
        assert result.updated >= 1
        assert result.skipped == 0
        assert result.warnings == []
        assert [match.context.id for match in after.matches] == [target.id]
        assert after.matches[0].vector_score is not None

    anyio.run(scenario)


def test_context_reindex_can_force_rebuild_for_pooling_changes(tmp_path: Path) -> None:
    """Force reindex should rebuild vectors even when model name and dimensions match."""

    async def scenario() -> None:
        async with (
            _temporary_database(tmp_path / "rag-force-reindex.db") as database,
            database.session() as session,
        ):
            repository = SqlAlchemyContextRepository(session=session)
            saved = await seed_context(
                session,
                kind=ContextKind.RESEARCH,
                title="Pooling upgrade target",
                summary="Existing vectors should rebuild under the new pooling behavior.",
                content="""# Pooling upgrade target

## Summary
semantic-target was embedded before the pooling change.
""",
                embedding_provider=KeywordEmbeddingProvider(),
            )
            await session.commit()

            before_chunk = await session.scalar(
                select(ContextChunkORM).where(ContextChunkORM.context_id == saved.id)
            )
            assert before_chunk is not None
            assert before_chunk.embedding == "[0,0,1]"

            upgraded_service = ContextService(
                repository=repository,
                embedding_provider=MeanPoolingUpgradeEmbeddingProvider(),
                vector_retrieval_enabled=True,
            )
            unchanged = await upgraded_service.reindex_embeddings(limit=10)
            assert unchanged.scanned == 0
            assert unchanged.updated == 0

            rebuilt = await upgraded_service.reindex_embeddings(limit=10, force=True)
            await session.refresh(before_chunk)

        assert rebuilt.scanned >= 1
        assert rebuilt.updated >= 1
        assert rebuilt.skipped == 0
        assert before_chunk.embedding == "[0,1,0]"

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
            exact = await seed_context(
                session,
                kind=ContextKind.HANDOFF,
                title="API handoff",
                summary="API tag should match exactly.",
                content=_handoff_content("API context."),
                tags=["api"],
                source_type=ContextSourceType.IMPORTED,
            )
            await seed_context(
                session,
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


def test_context_list_treats_sql_like_tag_filter_as_data(tmp_path: Path) -> None:
    """Tag filtering should bind SQL-looking values instead of widening results."""

    async def scenario() -> None:
        async with (
            _temporary_database(tmp_path / "sql-like-tags.db") as database,
            database.session() as session,
        ):
            service = ContextService(
                repository=SqlAlchemyContextRepository(session=session)
            )
            sql_like_tag = "rag' OR 1=1 --"
            exact = await seed_context(
                session,
                kind=ContextKind.HANDOFF,
                title="SQL-looking tag handoff",
                summary="SQL-looking tag should match exactly.",
                content=_handoff_content("Injection-looking tag context."),
                tags=[sql_like_tag],
            )
            await seed_context(
                session,
                kind=ContextKind.HANDOFF,
                title="Plain tag handoff",
                summary="Plain tag should not leak into SQL-looking filter.",
                content=_handoff_content("Plain tag context."),
                tags=["rag"],
            )
            await session.commit()

            listed, total = await service.list_contexts(tag=sql_like_tag)

        assert total == 1
        assert [item.id for item in listed] == [exact.id]

    anyio.run(scenario)


def test_context_list_filters_created_and_updated_date_ranges(tmp_path: Path) -> None:
    """Context Vault list filters should constrain created and updated date ranges."""

    async def scenario() -> None:
        async with (
            _temporary_database(tmp_path / "date-filters.db") as database,
            database.session() as session,
        ):
            service = ContextService(
                repository=SqlAlchemyContextRepository(session=session)
            )
            older = await seed_context(
                session,
                kind=ContextKind.HANDOFF,
                title="Older handoff",
                summary="Older context outside the requested date window.",
                content=_handoff_content("Older context."),
            )
            inside = await seed_context(
                session,
                kind=ContextKind.HANDOFF,
                title="Inside handoff",
                summary="Context inside the requested date window.",
                content=_handoff_content("Inside context."),
            )
            newer = await seed_context(
                session,
                kind=ContextKind.HANDOFF,
                title="Newer handoff",
                summary="Newer context outside the requested date window.",
                content=_handoff_content("Newer context."),
            )
            rows = {
                older.id: (
                    datetime(2026, 5, 17, 10, 0, tzinfo=UTC),
                    datetime(2026, 5, 17, 11, 0, tzinfo=UTC),
                ),
                inside.id: (
                    datetime(2026, 5, 18, 10, 0, tzinfo=UTC),
                    datetime(2026, 5, 18, 11, 0, tzinfo=UTC),
                ),
                newer.id: (
                    datetime(2026, 5, 19, 10, 0, tzinfo=UTC),
                    datetime(2026, 5, 19, 11, 0, tzinfo=UTC),
                ),
            }
            for context_id, (created_at, updated_at) in rows.items():
                model = await session.get(ContextORM, context_id)
                assert model is not None
                model.created_at = created_at
                model.updated_at = updated_at
            await session.commit()

            created_listed, created_total = await service.list_contexts(
                created_after=datetime(2026, 5, 18, 0, 0, tzinfo=UTC),
                created_before=datetime(2026, 5, 18, 23, 59, 59, tzinfo=UTC),
            )
            updated_listed, updated_total = await service.list_contexts(
                updated_after=datetime(2026, 5, 18, 0, 0, tzinfo=UTC),
                updated_before=datetime(2026, 5, 18, 23, 59, 59, tzinfo=UTC),
            )

        assert created_total == 1
        assert [item.id for item in created_listed] == [inside.id]
        assert updated_total == 1
        assert [item.id for item in updated_listed] == [inside.id]

    anyio.run(scenario)
