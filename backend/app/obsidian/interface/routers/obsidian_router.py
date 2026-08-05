"""Compatibility router assembling focused Obsidian route groups."""

from __future__ import annotations

from app.obsidian.interface.routers.obsidian_graph_projection_router import (
    graph_build_status,
    graph_projection_status,
    rebuild_graph_projection,
    router as graph_projection_router,
    validate_note_graph_links,
)
from app.obsidian.interface.routers.obsidian_librarian_router import (
    ask_obsidian_librarian,
    cancel_obsidian_librarian_workflow,
    get_obsidian_librarian_workflow,
    resume_obsidian_librarian_workflow,
    router as librarian_router,
    start_obsidian_librarian_workflow,
)
from app.obsidian.interface.routers.obsidian_note_router import (
    read_obsidian_note,
    read_obsidian_note_by_path,
    related_obsidian_notes,
    related_obsidian_notes_by_path,
    router as note_router,
    save_obsidian_note,
    search_obsidian_notes,
)
from app.obsidian.interface.routers.obsidian_vault_index_router import (
    initialize_obsidian_vault,
    obsidian_status,
    reindex_obsidian_vault,
    router as vault_index_router,
)
from fastapi import APIRouter

router = APIRouter(prefix="/obsidian", tags=["obsidian"])
router.include_router(vault_index_router)
router.include_router(note_router)
router.include_router(graph_projection_router)
router.include_router(librarian_router)

__all__ = [
    "ask_obsidian_librarian",
    "cancel_obsidian_librarian_workflow",
    "get_obsidian_librarian_workflow",
    "graph_build_status",
    "graph_projection_status",
    "initialize_obsidian_vault",
    "obsidian_status",
    "read_obsidian_note",
    "read_obsidian_note_by_path",
    "rebuild_graph_projection",
    "reindex_obsidian_vault",
    "related_obsidian_notes",
    "related_obsidian_notes_by_path",
    "resume_obsidian_librarian_workflow",
    "router",
    "save_obsidian_note",
    "search_obsidian_notes",
    "start_obsidian_librarian_workflow",
    "validate_note_graph_links",
]
