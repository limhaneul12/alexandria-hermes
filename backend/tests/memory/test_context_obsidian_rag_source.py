"""Context RAG behavior tests for Obsidian-backed Alexandria notes."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from pathlib import Path

import anyio
from app.memory.application.context_service import ContextService
from app.memory.domain.event_enum.context_enums import RagStrategy
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
from app.obsidian.infrastructure.repositories.obsidian_index_repository import (
    SqlAlchemyObsidianIndexRepository,
)
from app.retrieval.application.embedding_provider import EmbeddingProvider
from app.shared.infrastructure.database import Database

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
