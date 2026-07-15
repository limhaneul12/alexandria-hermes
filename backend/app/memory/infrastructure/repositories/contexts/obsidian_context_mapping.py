"""Map Obsidian index rows into Context RAG read models."""

from __future__ import annotations

from app.memory.domain.entities.context_read_models import (
    ContextChunkRecord,
    ContextRecord,
    ContextSearchMatch,
)
from app.memory.domain.event_enum.context_enums import (
    ContextContentFormat,
    ContextImportance,
    ContextKind,
    ContextScope,
    ContextSourceType,
    ContextStorageStatus,
)
from app.memory.domain.types.context_payload_types import ContextMetadataPayload
from app.obsidian.domain.event_enum.obsidian_enums import (
    AlexandriaNoteType,
    ObsidianIndexStatus,
)
from app.obsidian.infrastructure.models.obsidian_index_models import (
    ObsidianChunkORM,
    ObsidianFileORM,
)
from app.shared.types.extra_types import JSONValue
from app.shared.types.types_convert_utils import aware_utc_datetime

OBSIDIAN_CONTEXT_ID_PREFIX = "obsidian:"
OBSIDIAN_CHUNK_ID_PREFIX = "obsidian-chunk:"
OBSIDIAN_SOURCE_AGENT = "obsidian-vault"
DEFAULT_EXCLUDED_OBSIDIAN_RECALL_TYPES = frozenset(
    {AlexandriaNoteType.LIBRARIAN_CHAT.value}
)
DEFAULT_EXCLUDED_OBSIDIAN_RECALL_STATUSES = frozenset(
    {"archived", "deprecated", "superseded"}
)
DEFAULT_EXCLUDED_OBSIDIAN_RECALL_PREFIXES = ("_Ops/",)


def metadata_filters_present(
    *,
    workspace_id: str | None,
    agent_id: str | None,
    user_id: str | None,
    session_id: str | None,
) -> bool:
    return any(
        value is not None for value in (workspace_id, agent_id, user_id, session_id)
    )


def matches_context_filters(
    note: ObsidianFileORM,
    *,
    kind: ContextKind | None,
    include_scopes: list[ContextScope] | None,
) -> bool:
    if not is_default_recall_visible(note):
        return False
    context = context_record_from_obsidian_row(note)
    if kind is not None and context.kind != kind:
        return False
    return not (include_scopes and context.scope not in include_scopes)


def is_default_recall_visible(note: ObsidianFileORM) -> bool:
    """Return whether a note belongs in default agent recall.

    Args:
        note: Indexed Obsidian note row.

    Returns:
        True when the note is safe for default Context RAG recall.
    """
    if note.index_status != ObsidianIndexStatus.INDEXED.value:
        return False
    if note.alexandria_type in DEFAULT_EXCLUDED_OBSIDIAN_RECALL_TYPES:
        return False
    if note.status.lower() in DEFAULT_EXCLUDED_OBSIDIAN_RECALL_STATUSES:
        return False
    return not note.relative_path.startswith(DEFAULT_EXCLUDED_OBSIDIAN_RECALL_PREFIXES)


def match_from_obsidian_rows(
    *,
    note: ObsidianFileORM,
    chunk: ObsidianChunkORM,
    score: float,
    fts_score: float | None,
    vector_score: float | None,
    why_retrieved: str,
) -> ContextSearchMatch:
    context = context_record_from_obsidian_row(note)
    chunk_record = chunk_record_from_obsidian_row(chunk)
    return ContextSearchMatch(
        context=context,
        chunk=chunk_record,
        score=score,
        fts_score=fts_score,
        vector_score=vector_score,
        why_retrieved=why_retrieved,
    )


def context_record_from_obsidian_row(note: ObsidianFileORM) -> ContextRecord:
    metadata = _context_metadata(note)
    scope = _scope_from_note(note)
    return ContextRecord(
        id=f"{OBSIDIAN_CONTEXT_ID_PREFIX}{note.note_id}",
        kind=_kind_from_note(note),
        title=note.title,
        summary=_summary_from_note(note),
        content=note.body,
        content_format=ContextContentFormat.MARKDOWN,
        project=note.project,
        scope=scope,
        workspace_id=None,
        agent_id=None,
        user_id=None,
        session_id=None,
        visibility=scope,
        source_agent=note.source or OBSIDIAN_SOURCE_AGENT,
        source_type=ContextSourceType.IMPORTED,
        importance=ContextImportance.MEDIUM,
        tags=list(note.tags),
        status=ContextStorageStatus.SAVED,
        quality_score=100,
        warnings=[],
        restore_prompt=f"Open [[{note.relative_path.removesuffix('.md')}]]",
        context_metadata=metadata,
        created_at=aware_utc_datetime(note.modified_at),
        updated_at=aware_utc_datetime(note.indexed_at),
        last_accessed_at=None,
        expires_at=None,
        archived_at=None,
        access_count=0,
        is_archived=False,
    )


def chunk_record_from_obsidian_row(chunk: ObsidianChunkORM) -> ContextChunkRecord:
    metadata = ContextMetadataPayload(
        source_surface="obsidian_vault",
        obsidian_note_id=chunk.note_id,
    )
    return ContextChunkRecord(
        id=f"{OBSIDIAN_CHUNK_ID_PREFIX}{chunk.id}",
        context_id=f"{OBSIDIAN_CONTEXT_ID_PREFIX}{chunk.note_id}",
        chunk_index=chunk.chunk_index,
        heading=chunk.heading_path,
        content=chunk.text,
        token_count=chunk.token_count,
        content_hash=chunk.content_hash,
        chunk_metadata=metadata,
        created_at=aware_utc_datetime(chunk.created_at),
    )


def _context_metadata(note: ObsidianFileORM) -> ContextMetadataPayload:
    metadata = ContextMetadataPayload(
        source_surface="obsidian_vault",
        obsidian_note_id=note.note_id,
        relative_path=note.relative_path,
        alexandria_type=note.alexandria_type,
        index_status=note.index_status,
        wikilink=f"[[{note.relative_path.removesuffix('.md')}]]",
    )
    if note.source is not None:
        metadata["source"] = note.source
    return metadata


def _kind_from_note(note: ObsidianFileORM) -> ContextKind:
    frontmatter_kind = _context_kind_from_frontmatter(note.frontmatter_json)
    if frontmatter_kind is not None:
        return frontmatter_kind
    note_type = AlexandriaNoteType(note.alexandria_type)
    if note_type is AlexandriaNoteType.MEMORY_COMPACT:
        return ContextKind.COMPACT
    if note_type in {AlexandriaNoteType.SKILL, AlexandriaNoteType.PROMPT}:
        return ContextKind.USAGE
    if note_type in {
        AlexandriaNoteType.JOB_PLAN,
        AlexandriaNoteType.LIBRARIAN_BRIEF,
    }:
        return ContextKind.PLAN
    return ContextKind.MEMORY


def _context_kind_from_frontmatter(
    frontmatter: dict[str, JSONValue],
) -> ContextKind | None:
    value = frontmatter.get("context_kind") or frontmatter.get("kind")
    if not isinstance(value, str):
        return None
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    try:
        return ContextKind(normalized)
    except ValueError:
        return None


def _scope_from_note(note: ObsidianFileORM) -> ContextScope:
    value = note.frontmatter_json.get("scope")
    if isinstance(value, str):
        normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
        try:
            return ContextScope(normalized)
        except ValueError:
            pass
    if note.project:
        return ContextScope.PROJECT
    return ContextScope.GLOBAL


def _summary_from_note(note: ObsidianFileORM) -> str:
    value = note.frontmatter_json.get("summary")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return _excerpt(note.body)


def _excerpt(text: str, limit: int = 240) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 1]}…"


def raw_obsidian_chunk_id(chunk_id: str) -> str:
    return chunk_id.removeprefix(OBSIDIAN_CHUNK_ID_PREFIX)
