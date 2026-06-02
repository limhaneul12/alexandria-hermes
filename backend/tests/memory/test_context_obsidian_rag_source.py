"""Context RAG behavior tests for Obsidian-backed Alexandria notes."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from pathlib import Path

import anyio
from app.memory.application.context_service import ContextService
from app.memory.domain.event_enum.context_enums import (
    ContextKind,
    RagHealthState,
    RagStrategy,
)
from app.memory.infrastructure.models.context_models import ContextChunkORM
from app.memory.infrastructure.repositories.context_repository import (
    SqlAlchemyContextRepository,
)
from app.memory.infrastructure.repositories.contexts.obsidian_search_source import (
    SqlAlchemyObsidianContextSearchSource,
)
from app.obsidian.application.obsidian_service import ObsidianService
from app.obsidian.domain.contracts.obsidian_contracts import ObsidianSaveNote
from app.obsidian.domain.event_enum.obsidian_enums import AlexandriaNoteType
from app.obsidian.infrastructure.models import (
    obsidian_index_models as _obsidian_index_models,
)
from app.obsidian.infrastructure.models.obsidian_index_models import ObsidianChunkORM
from app.obsidian.infrastructure.repositories.obsidian_index_repository import (
    SqlAlchemyObsidianIndexRepository,
)
from app.retrieval.application.embedding_provider import EmbeddingProvider
from app.shared.infrastructure.database import Database
from sqlalchemy import func, select
from tests.memory.context_seed import seed_context

_OBSIDIAN_MODELS_LOADED = _obsidian_index_models


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


class UpgradedPoolingEmbeddingProvider(KeywordEmbeddingProvider):
    """Provider fake with same model/dimension but a changed fingerprint."""

    @property
    def provider_version(self) -> str:
        return "pooling-upgrade-v2"

    @property
    def pooling_mode(self) -> str:
        return "mean-v2"


@asynccontextmanager
async def _temporary_database(path: Path) -> AsyncIterator[Database]:
    database = Database(database_url=f"sqlite+aiosqlite:///{path}", create_schema=True)
    await database.initialize()
    try:
        yield database
    finally:
        await database.shutdown()


def test_context_rag_search_includes_obsidian_vault_fts_source(
    tmp_path: Path,
) -> None:
    """Context RAG should retrieve indexed Obsidian notes without duplicating data."""

    async def scenario() -> tuple[str, list[str], str]:
        async with (
            _temporary_database(tmp_path / "obsidian-rag.db") as database,
            database.session() as session,
        ):
            obsidian_service = ObsidianService(
                repository=SqlAlchemyObsidianIndexRepository(session=session),
                vault_path=str(tmp_path / "vault"),
                alexandria_root="Alexandria",
            )
            saved = await obsidian_service.save_note(
                ObsidianSaveNote(
                    title="Command Usage Handoff",
                    body=(
                        "# Command Usage Handoff\n\n"
                        "agent-remote command usage is dogfood-ready."
                    ),
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="command_usage_handoff",
                    tags=["commands", "usage"],
                    project="omx-agent-adapter",
                    source="codex",
                )
            )
            service = ContextService(
                repository=SqlAlchemyContextRepository(session=session),
                extra_search_sources=[
                    SqlAlchemyObsidianContextSearchSource(session=session)
                ],
            )
            pack = await service.search(
                query="command usage",
                strategy=RagStrategy.FTS_ONLY,
                limit=5,
                project="omx-agent-adapter",
            )

        return (
            saved.note_id,
            [match.context.id for match in pack.matches],
            pack.context_pack,
        )

    note_id, context_ids, context_pack = anyio.run(scenario)

    assert set(context_ids) == {f"obsidian:{note_id}"}
    assert "Command Usage Handoff" in context_pack
    assert "obsidian:" in context_pack


def test_context_embedding_reindex_backfills_obsidian_chunks_for_vector_search(
    tmp_path: Path,
) -> None:
    """Context embedding reindex should make Obsidian chunks vector-searchable."""

    async def scenario() -> tuple[int, int, list[str]]:
        async with (
            _temporary_database(tmp_path / "obsidian-vector-rag.db") as database,
            database.session() as session,
        ):
            obsidian_service = ObsidianService(
                repository=SqlAlchemyObsidianIndexRepository(session=session),
                vault_path=str(tmp_path / "vault"),
                alexandria_root="Alexandria",
            )
            await obsidian_service.save_note(
                ObsidianSaveNote(
                    title="Semantic Target Note",
                    body="# Semantic Target\n\nsemantic-target belongs to the vault.",
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="semantic_target_note",
                    project="omx-agent-adapter",
                )
            )
            await obsidian_service.save_note(
                ObsidianSaveNote(
                    title="Distractor Note",
                    body="# Distractor\n\ndistractor belongs elsewhere.",
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="distractor_note",
                    project="omx-agent-adapter",
                )
            )
            service = ContextService(
                repository=SqlAlchemyContextRepository(session=session),
                embedding_provider=KeywordEmbeddingProvider(),
                vector_retrieval_enabled=True,
                extra_search_sources=[
                    SqlAlchemyObsidianContextSearchSource(session=session)
                ],
            )

            before = await service.search(
                query="query-alias",
                strategy=RagStrategy.VECTOR_ONLY,
                limit=1,
                project="omx-agent-adapter",
            )
            result = await service.reindex_embeddings(limit=10)
            after = await service.search(
                query="query-alias",
                strategy=RagStrategy.VECTOR_ONLY,
                limit=1,
                project="omx-agent-adapter",
            )

        assert before.matches == []
        return (
            result.scanned,
            result.updated,
            [match.context.id for match in after.matches],
        )

    scanned, updated, context_ids = anyio.run(scenario)

    assert scanned >= 2
    assert updated >= 2
    assert context_ids == ["obsidian:semantic_target_note"]


def test_context_rag_status_detects_obsidian_embedding_fingerprint_mismatch(
    tmp_path: Path,
) -> None:
    """Obsidian source vectors should be blocked until fingerprint reindex runs."""

    async def scenario() -> tuple[str, str, int, list[str], list[str | None]]:
        async with (
            _temporary_database(tmp_path / "obsidian-fingerprint-rag.db") as database,
            database.session() as session,
        ):
            obsidian_service = ObsidianService(
                repository=SqlAlchemyObsidianIndexRepository(session=session),
                vault_path=str(tmp_path / "vault"),
                alexandria_root="Alexandria",
            )
            await obsidian_service.save_note(
                ObsidianSaveNote(
                    title="Semantic Target Note",
                    body="# Semantic Target\n\nsemantic-target belongs to the vault.",
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="semantic_target_note",
                    project="omx-agent-adapter",
                )
            )
            old_service = ContextService(
                repository=SqlAlchemyContextRepository(session=session),
                embedding_provider=KeywordEmbeddingProvider(),
                vector_retrieval_enabled=True,
                extra_search_sources=[
                    SqlAlchemyObsidianContextSearchSource(session=session)
                ],
            )
            await old_service.reindex_embeddings(limit=10)

            upgraded_service = ContextService(
                repository=SqlAlchemyContextRepository(session=session),
                embedding_provider=UpgradedPoolingEmbeddingProvider(),
                vector_retrieval_enabled=True,
                extra_search_sources=[
                    SqlAlchemyObsidianContextSearchSource(session=session)
                ],
            )
            health = await upgraded_service.rag_health_with_index_status()
            before = await upgraded_service.search(
                query="query-alias",
                strategy=RagStrategy.VECTOR_ONLY,
                limit=1,
                project="omx-agent-adapter",
            )
            rebuilt = await upgraded_service.reindex_embeddings(limit=10)
            after = await upgraded_service.search(
                query="query-alias",
                strategy=RagStrategy.VECTOR_ONLY,
                limit=1,
                project="omx-agent-adapter",
            )
            chunks = await session.scalars(select(ObsidianChunkORM))

        return (
            health.embedding.value,
            before.effective_strategy.value,
            rebuilt.updated,
            [match.context.id for match in after.matches],
            [chunk.embedding_pooling_mode for chunk in chunks.all()],
        )

    health_status, before_strategy, updated, context_ids, pooling_modes = anyio.run(
        scenario
    )

    assert health_status == RagHealthState.REINDEX_REQUIRED.value
    assert before_strategy == RagStrategy.FTS_ONLY.value
    assert updated >= 1
    assert context_ids == ["obsidian:semantic_target_note"]
    assert "mean-v2" in pooling_modes


def test_context_soft_rebuild_prioritizes_stale_obsidian_before_current_context(
    tmp_path: Path,
) -> None:
    """Soft rebuild batches should update stale sources before current chunks."""

    async def scenario() -> tuple[int, str, list[str | None], list[str | None]]:
        async with (
            _temporary_database(tmp_path / "cross-source-soft-rebuild.db") as database,
            database.session() as session,
        ):
            repository = SqlAlchemyContextRepository(session=session)
            obsidian_source = SqlAlchemyObsidianContextSearchSource(session=session)
            obsidian_service = ObsidianService(
                repository=SqlAlchemyObsidianIndexRepository(session=session),
                vault_path=str(tmp_path / "vault"),
                alexandria_root="Alexandria",
            )
            await obsidian_service.save_note(
                ObsidianSaveNote(
                    title="Stale Obsidian Target",
                    body="# Semantic Target\n\nsemantic-target belongs to the vault.",
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="stale_obsidian_target",
                    project="omx-agent-adapter",
                )
            )
            old_service = ContextService(
                repository=repository,
                embedding_provider=KeywordEmbeddingProvider(),
                vector_retrieval_enabled=True,
                extra_search_sources=[obsidian_source],
            )
            await old_service.reindex_embeddings(limit=10)

            await seed_context(
                session,
                kind=ContextKind.RESEARCH,
                title="Current Context Target",
                summary="Already matches the upgraded fingerprint.",
                content="# Current Context\n\nsemantic-target already current.",
                project="omx-agent-adapter",
                embedding_provider=UpgradedPoolingEmbeddingProvider(),
            )
            await session.commit()

            service = ContextService(
                repository=repository,
                embedding_provider=UpgradedPoolingEmbeddingProvider(),
                vector_retrieval_enabled=True,
                extra_search_sources=[obsidian_source],
            )
            report = await service.soft_rebuild_embeddings(limit=1)
            context_chunks = await session.scalars(select(ContextChunkORM))
            obsidian_chunks = await session.scalars(
                select(ObsidianChunkORM).where(
                    func.length(func.trim(ObsidianChunkORM.text)) > 0
                )
            )

        return (
            report.reindex.updated,
            report.after.embedding.value,
            [chunk.embedding_pooling_mode for chunk in context_chunks.all()],
            [chunk.embedding_pooling_mode for chunk in obsidian_chunks.all()],
        )

    updated, after_status, context_pooling, obsidian_pooling = anyio.run(scenario)

    assert updated == 1
    assert after_status == RagHealthState.HEALTHY.value
    assert context_pooling == ["mean-v2"]
    assert obsidian_pooling == ["mean-v2"]
