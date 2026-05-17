"""Behavior tests for Context Vault repository contracts."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from pathlib import Path

import anyio
import pytest
from app.memory.application.context_service import ContextService
from app.memory.domain.event_enum.context_enums import (
    ContextAccessActorType,
    ContextAccessMethod,
    ContextKind,
    ContextSourceType,
    ContextStorageStatus,
    RagHealthState,
    RagStrategy,
)
from app.memory.infrastructure.repositories.context_repository import (
    SqlAlchemyContextRepository,
)
from app.retrieval.application.embedding_provider import EmbeddingProvider
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
            target = await service.save(
                kind=ContextKind.RESEARCH,
                title="Semantic target",
                summary="Embedding-only context.",
                content="""# Semantic target

## Summary
Embedding-only context.

## Evidence
semantic-target carries vector meaning only.
""",
            )
            await service.save(
                kind=ContextKind.RESEARCH,
                title="Distractor",
                summary="Different embedding.",
                content="""# Distractor

## Summary
Different embedding.

## Evidence
distractor should rank behind the semantic target.
""",
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
            target = await service.save(
                kind=ContextKind.RESEARCH,
                title="Bound parameter target",
                summary="semantic-target belongs to the SQL-looking project.",
                content="""# Bound parameter target

## Summary
semantic-target belongs to the SQL-looking project.
""",
                project=sql_like_project,
            )
            await service.save(
                kind=ContextKind.RESEARCH,
                title="Other semantic target",
                summary="semantic-target belongs to another project.",
                content="""# Other semantic target

## Summary
semantic-target belongs to another project.
""",
                project="other-project",
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
            target = await service.save(
                kind=ContextKind.RESEARCH,
                title="FTS bound target",
                summary="sharedmarker belongs to the SQL-looking project.",
                content="""# FTS bound target

## Summary
sharedmarker belongs to the SQL-looking project.
""",
                project=sql_like_project,
            )
            await service.save(
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
            target = await service.save(
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
            disabled_service = ContextService(repository=repository)
            target = await disabled_service.save(
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
            exact = await service.save(
                kind=ContextKind.HANDOFF,
                title="SQL-looking tag handoff",
                summary="SQL-looking tag should match exactly.",
                content=_handoff_content("Injection-looking tag context."),
                tags=[sql_like_tag],
            )
            await service.save(
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
