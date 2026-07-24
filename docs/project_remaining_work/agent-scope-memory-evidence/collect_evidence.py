"""Collect isolated acceptance evidence for the Version 2 scope-memory PRD."""

from __future__ import annotations

import json
import math
import os
import shutil
import tempfile
from pathlib import Path
from time import perf_counter

import anyio
from app.memory.application.context_service import ContextService
from app.memory.domain.event_enum.context_enums import ContextScope, RagStrategy
from app.memory.infrastructure.repositories.context_repository import (
    SqlAlchemyContextRepository,
)
from app.memory.infrastructure.repositories.contexts.obsidian_search_source import (
    SqlAlchemyObsidianContextSearchSource,
)
from app.obsidian.application.service.obsidian_service import ObsidianService
from app.obsidian.domain.contracts.obsidian_contracts import ObsidianSaveNote
from app.obsidian.domain.event_enum.obsidian_enums import AlexandriaNoteType
from app.obsidian.infrastructure.models.obsidian_index_models import (
    ObsidianChunkORM,
    ObsidianFileORM,
)
from app.obsidian.infrastructure.repositories.obsidian_index_repository import (
    SqlAlchemyObsidianIndexRepository,
)
from sqlalchemy import delete, select
from tests.memory.test_context_obsidian_rag_source import (
    KeywordEmbeddingProvider,
    _temporary_database,
)

EVIDENCE_DIR = Path(os.environ["EVIDENCE_DIR"])
TEST_RUN_ID = os.environ["TEST_RUN_ID"]
GIT_COMMIT_SHA = os.environ["GIT_COMMIT_SHA"]


def _p95_ms(values: list[float]) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return round(ordered[index] * 1000, 3)


def _fixtures() -> tuple[ObsidianSaveNote, ...]:
    return (
        ObsidianSaveNote(
            title="A Agent Memory",
            body="# A Agent Memory\n\nscope-evidence-token agent A.",
            alexandria_type=AlexandriaNoteType.CONTEXT,
            note_id="ctx_agent_a",
            project="agent-platform",
            status="current",
            frontmatter={
                "scope": "AGENT",
                "agent_id": "hermes-coding",
                "workspace_id": "default",
                "visibility": "PROJECT",
                "version": 3,
                "provenance": {
                    "source_actor_id": "hermes-coding",
                    "source_actor_type": "AGENT",
                    "source_run_id": "run-001",
                    "external_run_id": "external-001",
                    "artifact_refs": ["artifact://test-results.json"],
                    "evidence_refs": ["context://decision-001"],
                    "confidence": "HIGH",
                },
            },
        ),
        ObsidianSaveNote(
            title="B Agent Memory",
            body="# B Agent Memory\n\nscope-evidence-token agent B.",
            alexandria_type=AlexandriaNoteType.CONTEXT,
            note_id="ctx_agent_b",
            project="agent-platform",
            status="current",
            frontmatter={
                "scope": "AGENT",
                "agent_id": "hermes-research",
                "workspace_id": "default",
            },
        ),
        ObsidianSaveNote(
            title="A Session Memory",
            body="# A Session Memory\n\nscope-evidence-token session A.",
            alexandria_type=AlexandriaNoteType.CONTEXT,
            note_id="ctx_session_a",
            project="agent-platform",
            status="current",
            frontmatter={
                "scope": "SESSION",
                "session_id": "session-a",
                "workspace_id": "default",
            },
        ),
        ObsidianSaveNote(
            title="Shared Project Memory",
            body="# Shared Project Memory\n\nscope-evidence-token shared project.",
            alexandria_type=AlexandriaNoteType.CONTEXT,
            note_id="ctx_project_shared",
            project="agent-platform",
            status="current",
            frontmatter={"scope": "PROJECT", "workspace_id": "default"},
        ),
    )


async def _collect(root: Path) -> dict[str, object]:
    vault_path = root / "vault"
    save_durations: list[float] = []
    async with (
        _temporary_database(root / "acceptance.db") as database,
        database.session() as session,
    ):
        obsidian = ObsidianService(
            repository=SqlAlchemyObsidianIndexRepository(session=session),
            vault_path=str(vault_path),
            alexandria_root="Alexandria",
        )
        for fixture in _fixtures():
            started = perf_counter()
            await obsidian.save_note(fixture)
            save_durations.append(perf_counter() - started)

        generated = (
            vault_path / "Alexandria" / "Contexts" / "Projects" / "A Agent Memory.md"
        )
        shutil.copyfile(generated, EVIDENCE_DIR / "generated-agent-context.md")

        await session.execute(delete(ObsidianChunkORM))
        await session.execute(delete(ObsidianFileORM))
        await session.commit()
        reindex = await obsidian.reindex()

        indexed = await session.scalars(
            select(ObsidianFileORM).order_by(ObsidianFileORM.note_id)
        )
        restored = {
            row.note_id: {
                key: row.frontmatter_json.get(key)
                for key in (
                    "scope",
                    "project",
                    "workspace_id",
                    "agent_id",
                    "session_id",
                    "status",
                    "version",
                    "content_hash",
                    "source_actor_id",
                    "source_run_id",
                )
            }
            for row in indexed.all()
        }
        service = ContextService(
            repository=SqlAlchemyContextRepository(session=session),
            embedding_provider=KeywordEmbeddingProvider(),
            vector_retrieval_enabled=True,
            extra_search_sources=[
                SqlAlchemyObsidianContextSearchSource(session=session)
            ],
        )
        await service.reindex_embeddings(limit=20, force=True)

        async def search(strategy: RagStrategy) -> list[str]:
            pack = await service.search(
                query="scope-evidence-token",
                strategy=strategy,
                limit=10,
                project="agent-platform",
                agent_id="hermes-coding",
                workspace_id="default",
                include_scopes=[ContextScope.AGENT, ContextScope.PROJECT],
            )
            return [match.context.id for match in pack.matches]

        results = {strategy.value: await search(strategy) for strategy in RagStrategy}
        fts_times: list[float] = []
        hybrid_times: list[float] = []
        for _ in range(40):
            started = perf_counter()
            await search(RagStrategy.FTS_ONLY)
            fts_times.append(perf_counter() - started)
            started = perf_counter()
            await search(RagStrategy.HYBRID)
            hybrid_times.append(perf_counter() - started)

    return {
        "reindex": {
            "files_seen": reindex.files_seen,
            "files_indexed": reindex.files_indexed,
            "files_skipped": reindex.files_skipped,
            "stale_marked": reindex.stale_marked,
            "errors": reindex.errors,
        },
        "restored_frontmatter": restored,
        "recall_results": results,
        "performance": {
            "sample_count": 40,
            "fts_recall_p95_ms": _p95_ms(fts_times),
            "hybrid_recall_p95_ms": _p95_ms(hybrid_times),
            "context_save_p95_ms": _p95_ms(save_durations),
            "targets_ms": {
                "fts_recall": 500,
                "hybrid_recall": 2000,
                "context_save": 1000,
            },
        },
    }


def main() -> None:
    with tempfile.TemporaryDirectory(
        prefix="alexandria-version2-evidence-"
    ) as temporary_directory:
        result = anyio.run(_collect, Path(temporary_directory))
    metadata = {"test_run_id": TEST_RUN_ID, "git_commit_sha": GIT_COMMIT_SHA}
    (EVIDENCE_DIR / "reindex-result.json").write_text(
        json.dumps(
            {
                **metadata,
                **result["reindex"],
                "restored_frontmatter": result["restored_frontmatter"],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (EVIDENCE_DIR / "recall-results.json").write_text(
        json.dumps(
            {**metadata, "strategies": result["recall_results"]},
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (EVIDENCE_DIR / "performance.json").write_text(
        json.dumps(
            {**metadata, **result["performance"]},
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result["performance"], ensure_ascii=False))


if __name__ == "__main__":
    main()
