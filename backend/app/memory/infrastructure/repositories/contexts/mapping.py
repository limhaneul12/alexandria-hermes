"""Mapping helpers for Context Vault ORM rows."""

from __future__ import annotations

from app.memory.domain.entities.context_read_models import (
    ContextChunkRecord,
    ContextRecord,
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
from app.memory.infrastructure.models.context_models import ContextChunkORM, ContextORM
from app.shared.types.extra_types import JSONValue


def _string_list(value: JSONValue) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _json_object(value: JSONValue) -> ContextMetadataPayload:
    payload: ContextMetadataPayload = {}
    if not isinstance(value, dict):
        return payload
    payload.update(value.items())
    return payload


def map_context_row(row: ContextORM) -> ContextRecord:
    """Map a context ORM row into a read model.

    Args:
        row: Context ORM row.

    Returns:
        Context read model.
    """
    context = ContextRecord(
        id=row.id,
        kind=ContextKind(row.kind),
        title=row.title,
        summary=row.summary,
        content=row.content,
        content_format=ContextContentFormat(row.content_format),
        project=row.project,
        scope=ContextScope(row.scope),
        workspace_id=row.workspace_id,
        agent_id=row.agent_id,
        user_id=row.user_id,
        session_id=row.session_id,
        visibility=ContextScope(row.visibility),
        source_agent=row.source_agent,
        source_type=ContextSourceType(row.source_type),
        importance=ContextImportance(row.importance),
        tags=_string_list(row.tags),
        status=ContextStorageStatus(row.status),
        quality_score=row.quality_score,
        warnings=_string_list(row.warnings),
        restore_prompt=row.restore_prompt,
        context_metadata=_json_object(row.context_metadata),
        created_at=row.created_at,
        updated_at=row.updated_at,
        last_accessed_at=row.last_accessed_at,
        expires_at=row.expires_at,
        archived_at=row.archived_at,
        access_count=row.access_count,
        is_archived=row.is_archived,
    )
    return context


def map_chunk_row(row: ContextChunkORM) -> ContextChunkRecord:
    """Map a context chunk ORM row into a read model.

    Args:
        row: Context chunk ORM row.

    Returns:
        Context chunk read model.
    """
    chunk = ContextChunkRecord(
        id=row.id,
        context_id=row.context_id,
        chunk_index=row.chunk_index,
        heading=row.heading,
        content=row.content,
        token_count=row.token_count,
        content_hash=row.content_hash,
        chunk_metadata=_json_object(row.chunk_metadata),
        created_at=row.created_at,
    )
    return chunk
