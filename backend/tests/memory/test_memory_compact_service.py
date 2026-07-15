"""Memory Compact service behavior tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import anyio
import pytest
from app.memory.application.memory_compact_service import MemoryCompactService
from app.memory.domain.event_enum.memory_compact_enums import (
    MemoryCompactStatus,
)
from app.memory.domain.repositories.memory_compact_repository import (
    MemoryCompactCreate,
    MemoryCompactSourceRefCreate,
)
from app.memory.infrastructure.repositories.memory_compact_repository import (
    ObsidianMemoryCompactRepository,
)
from app.shared.exceptions import MemoryCompactValidationError


def _service(vault_path: Path) -> MemoryCompactService:
    return MemoryCompactService(
        repository=ObsidianMemoryCompactRepository(
            vault_path=vault_path,
            relative_dir="Alexandria/Memory Compacts",
        )
    )


def _source_ref(source_id: str = "ctx-1") -> MemoryCompactSourceRefCreate:
    return MemoryCompactSourceRefCreate(
        source_type="CONTEXT",
        source_id=source_id,
        title="Context source",
        detail_path=f"/memory/contexts/{source_id}",
    )


def _create(status: MemoryCompactStatus) -> MemoryCompactCreate:
    return MemoryCompactCreate(
        project="alexandria-hermes",
        covered_from=datetime(2026, 5, 1, tzinfo=UTC),
        covered_to=datetime(2026, 5, 10, tzinfo=UTC),
        markdown_body="## 2026-05-01 to 2026-05-10\nDurable summary.",
        status=status,
        source_refs=[_source_ref()],
    )


def test_memory_compact_service_writes_obsidian_note_when_created(
    tmp_path: Path,
) -> None:
    """Memory Compact creation should persist a frontmatter Markdown note."""

    async def scenario() -> None:
        service = _service(tmp_path / "vault")
        compact = await service.create(_create(MemoryCompactStatus.CURRENT))
        note_path = (
            tmp_path / "vault" / "Alexandria" / "Memory Compacts" / f"{compact.id}.md"
        )
        note = note_path.read_text(encoding="utf-8")

        assert note_path.exists()
        assert "alexandria_type: 'memory_compact'" in note
        assert f"id: '{compact.id}'" in note
        assert "status: 'CURRENT'" in note
        assert "source_refs:" in note
        assert note.endswith("Durable summary.\n")

    anyio.run(scenario)


def test_memory_compact_service_supersedes_previous_current_when_new_current_created(
    tmp_path: Path,
) -> None:
    """Project should have one CURRENT compact and supersede prior notes."""

    async def scenario() -> None:
        service = _service(tmp_path / "vault")
        first = await service.create(_create(MemoryCompactStatus.CURRENT))
        second_payload = _create(MemoryCompactStatus.CURRENT)
        second = await service.create(
            MemoryCompactCreate(
                project=second_payload.project,
                covered_from=datetime(2026, 5, 11, tzinfo=UTC),
                covered_to=datetime(2026, 5, 15, tzinfo=UTC),
                markdown_body="## 2026-05-11 to 2026-05-15\nNew durable summary.",
                status=MemoryCompactStatus.CURRENT,
                source_refs=[_source_ref("ctx-2")],
            )
        )
        current = await service.current(project="alexandria-hermes")
        previous = await service.get(first.id)
        listed, total = await service.list_compacts(project="alexandria-hermes")

        assert total == 2
        assert current.id == second.id
        assert previous.status is MemoryCompactStatus.SUPERSEDED
        assert [item.id for item in listed] == [second.id, first.id]

    anyio.run(scenario)


def test_current_memory_compact_requires_source_refs(tmp_path: Path) -> None:
    """Current compacts should not be accepted without source refs."""

    async def scenario() -> None:
        service = _service(tmp_path / "vault")
        with pytest.raises(MemoryCompactValidationError, match="source refs"):
            await service.create(
                MemoryCompactCreate(
                    project="alexandria-hermes",
                    covered_from=datetime(2026, 5, 1, tzinfo=UTC),
                    covered_to=datetime(2026, 5, 10, tzinfo=UTC),
                    markdown_body="## 2026-05-01 to 2026-05-10\nNo refs.",
                    status=MemoryCompactStatus.CURRENT,
                    source_refs=[],
                )
            )

    anyio.run(scenario)


def test_memory_compact_service_lists_legacy_obsidian_notes(
    tmp_path: Path,
) -> None:
    """Legacy Obsidian Memory Compact notes should stay visible to the API."""

    async def scenario() -> None:
        vault = tmp_path / "vault"
        notes_dir = vault / "Alexandria" / "Memory Compacts"
        notes_dir.mkdir(parents=True)
        (notes_dir / "legacy compact.md").write_text(
            """---
alexandria_type: memory_compact
title: Legacy Compact
id: legacy-compact
project: alexandria-hermes
status: current
created: 2026-05-28
tags:
  - memory-compact
---
# Legacy Compact

Durable legacy summary.
""",
            encoding="utf-8",
        )

        service = _service(vault)
        current = await service.current(project="alexandria-hermes")
        listed, total = await service.list_compacts(project="alexandria-hermes")

        assert total == 1
        assert listed == [current]
        assert current.id == "legacy-compact"
        assert current.status is MemoryCompactStatus.CURRENT
        assert current.markdown_body == "# Legacy Compact\n\nDurable legacy summary."
        assert current.covered_from == datetime(2026, 5, 28, tzinfo=UTC)
        assert current.covered_to == datetime(2026, 5, 28, tzinfo=UTC)

    anyio.run(scenario)
