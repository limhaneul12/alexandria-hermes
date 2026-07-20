"""Obsidian edge index and related-note retrieval behavior tests."""

from __future__ import annotations

from pathlib import Path

import anyio
from app.obsidian.application.graph.obsidian_graph_service import ObsidianGraphService
from app.obsidian.application.service.obsidian_service import ObsidianService
from app.obsidian.domain.contracts.obsidian_contracts import ObsidianSaveNote
from app.obsidian.domain.event_enum.obsidian_enums import AlexandriaNoteType
from app.obsidian.infrastructure.models import (
    obsidian_index_models as _obsidian_index_models,
)
from app.obsidian.infrastructure.models.obsidian_index_models import ObsidianEdgeORM
from app.obsidian.infrastructure.repositories.obsidian_index_repository import (
    SqlAlchemyObsidianIndexRepository,
)
from app.shared.infrastructure.database import Database
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

_OBSIDIAN_MODELS_LOADED = _obsidian_index_models


def _database_url(path: Path) -> str:
    return f"sqlite+aiosqlite:///{path}"


async def _services(
    tmp_path: Path,
) -> tuple[Database, AsyncSession, ObsidianService, ObsidianGraphService]:
    database = Database(
        database_url=_database_url(tmp_path / "obsidian.db"), create_schema=True
    )
    await database.initialize()
    session = database.session()
    repository = SqlAlchemyObsidianIndexRepository(session=session)
    obsidian = ObsidianService(
        repository=repository,
        vault_path=str(tmp_path / "vault"),
        alexandria_root="Alexandria",
    )
    graph = ObsidianGraphService(repository=repository, obsidian_service=obsidian)
    return database, session, obsidian, graph


def test_reindex_builds_edges_and_related_notes_from_markdown(tmp_path: Path) -> None:
    """Related-note retrieval should use edges rebuilt from Obsidian Markdown."""

    async def scenario() -> tuple[list[tuple[str, str, str]], str]:
        database, session, obsidian, graph = await _services(tmp_path)
        try:
            start = await obsidian.save_note(
                ObsidianSaveNote(
                    title="Alexandria START HERE",
                    body="# Start\n\nCanonical root note.",
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="alexandria_start_here",
                    relative_path="Alexandria/START_HERE.md",
                    tags=["start"],
                )
            )
            current = await obsidian.save_note(
                ObsidianSaveNote(
                    title="Graph Current",
                    body="# Graph Current\n\nThis cites [[START_HERE]].",
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="ctx_graph_current",
                    frontmatter={
                        "source_refs": [
                            {
                                "id": start.note_id,
                                "path": "START_HERE.md",
                                "relation": "cites",
                            }
                        ]
                    },
                )
            )
            related = await graph.related_notes_by_path(current.relative_path)
        finally:
            await session.close()
            await database.shutdown()
        return [
            (item.note.note_id, item.relation.value, item.direction) for item in related
        ], current.relative_path

    related, current_path = anyio.run(scenario)

    assert current_path == "Alexandria/Contexts/Projects/Graph Current.md"
    assert related[0] == ("alexandria_start_here", "cites", "outgoing")


def test_reindex_resolves_relative_wikilinks_from_source_folder(
    tmp_path: Path,
) -> None:
    """Relative wikilinks should resolve against the source note folder."""

    async def scenario() -> tuple[
        list[tuple[str, str, str]],
        list[tuple[str, str]],
    ]:
        database, session, obsidian, graph = await _services(tmp_path)
        root = tmp_path / "vault" / "Alexandria"
        source_path = root / "A Source.md"
        target_path = root / "Z Target.md"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text(
            "---\n"
            "alexandria_type: context\n"
            "id: ctx_a_source\n"
            "title: Source\n"
            "status: active\n"
            "---\n"
            "# Source\n\nSee [[Z Target]].\n",
            encoding="utf-8",
        )
        target_path.write_text(
            "---\n"
            "alexandria_type: context\n"
            "id: ctx_z_target\n"
            "title: Target\n"
            "status: active\n"
            "---\n"
            "# Target\n",
            encoding="utf-8",
        )
        try:
            await obsidian.reindex()
            related = await graph.related_notes_by_path("Alexandria/A Source.md")
            rows = await session.execute(
                select(ObsidianEdgeORM.target_path, ObsidianEdgeORM.target_note_id)
            )
            indexed_edges = [(path, note_id or "") for path, note_id in rows.all()]
        finally:
            await session.close()
            await database.shutdown()
        return (
            [
                (item.note.note_id, item.relation.value, item.direction)
                for item in related
            ],
            indexed_edges,
        )

    related, indexed_edges = anyio.run(scenario)

    assert related == [("ctx_z_target", "wikilink", "outgoing")]
    assert indexed_edges == [("Alexandria/Z Target.md", "ctx_z_target")]


def test_repository_resolves_edges_after_target_note_is_indexed_later(
    tmp_path: Path,
) -> None:
    """A second resolve pass should fill target ids for late-indexed notes."""

    async def scenario() -> tuple[int, list[tuple[str, str]]]:
        database, session, obsidian, _graph = await _services(tmp_path)
        repository = SqlAlchemyObsidianIndexRepository(session=session)
        try:
            await obsidian.save_note(
                ObsidianSaveNote(
                    title="Late Source",
                    body="# Late Source\n\nSee [[Late Target]].",
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="ctx_late_source",
                    relative_path="Alexandria/Late Source.md",
                )
            )
            await obsidian.save_note(
                ObsidianSaveNote(
                    title="Late Target",
                    body="# Late Target\n",
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="ctx_late_target",
                    relative_path="Alexandria/Late Target.md",
                )
            )
            resolved = await repository.resolve_edge_targets()
            rows = await session.execute(
                select(ObsidianEdgeORM.target_path, ObsidianEdgeORM.target_note_id)
            )
            edges = [(path, note_id or "") for path, note_id in rows.all()]
        finally:
            await session.close()
            await database.shutdown()
        return resolved, edges

    resolved, edges = anyio.run(scenario)

    assert resolved == 1
    assert edges == [("Alexandria/Late Target.md", "ctx_late_target")]


def test_related_notes_include_incoming_backlinks(tmp_path: Path) -> None:
    """A target note should show notes that link to it as incoming relations."""

    async def scenario() -> list[tuple[str, str]]:
        database, session, obsidian, graph = await _services(tmp_path)
        try:
            await obsidian.save_note(
                ObsidianSaveNote(
                    title="Target",
                    body="# Target\n\nDestination.",
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="ctx_target",
                    relative_path="Alexandria/Target.md",
                )
            )
            await obsidian.save_note(
                ObsidianSaveNote(
                    title="Source",
                    body="# Source\n\nSee [[Target]].",
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="ctx_source",
                    relative_path="Alexandria/Source.md",
                )
            )
            related = await graph.related_notes("ctx_target")
        finally:
            await session.close()
            await database.shutdown()
        return [(item.note.note_id, item.direction) for item in related]

    assert anyio.run(scenario) == [("ctx_source", "incoming")]
