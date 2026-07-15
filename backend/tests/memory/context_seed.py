"""Test helpers for seeding Context Vault read/index fixtures."""

from __future__ import annotations

from datetime import datetime

from app.memory.domain.entities.context_read_models import ContextRecord
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
from app.memory.infrastructure.repositories.contexts.fts import (
    ensure_context_chunk_fts_table,
)
from app.memory.infrastructure.repositories.contexts.mapping import map_context_row
from app.memory.application.retrieval.chunker import chunk_markdown
from app.memory.application.retrieval.embedding_provider import EmbeddingProvider
from app.memory.application.retrieval.vector_serialization import vector_to_sqlite_json
from app.shared.types.types_convert_utils import now_utc
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

INSERT_CONTEXT_CHUNK_FTS_SQL = """
INSERT INTO context_chunk_fts (
    chunk_id,
    context_id,
    title,
    summary,
    content,
    kind,
    project,
    source_agent,
    tags,
    scope,
    workspace_id,
    agent_id,
    user_id,
    session_id,
    heading
) VALUES (
    :chunk_id,
    :context_id,
    :title,
    :summary,
    :content,
    :kind,
    :project,
    :source_agent,
    :tags,
    :scope,
    :workspace_id,
    :agent_id,
    :user_id,
    :session_id,
    :heading
)
"""


async def seed_context(
    session: AsyncSession,
    *,
    kind: ContextKind = ContextKind.HANDOFF,
    title: str = "Seeded handoff",
    summary: str = "Seeded context for retrieval tests.",
    content: str,
    project: str | None = None,
    scope: ContextScope = ContextScope.PROJECT,
    workspace_id: str | None = None,
    agent_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    visibility: ContextScope = ContextScope.PROJECT,
    source_agent: str = "Hermes",
    source_type: ContextSourceType = ContextSourceType.AGENT,
    importance: ContextImportance = ContextImportance.MEDIUM,
    tags: list[str] | None = None,
    status: ContextStorageStatus = ContextStorageStatus.SAVED,
    quality_score: int = 100,
    warnings: list[str] | None = None,
    restore_prompt: str | None = None,
    context_metadata: ContextMetadataPayload | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    embedding_provider: EmbeddingProvider | None = None,
) -> ContextRecord:
    """Seed a context row, chunk rows, and FTS rows for read-path tests.

    Args:
        session: Active test database session.
        content: Markdown content to chunk and index.
        embedding_provider: Optional deterministic embedding provider for
            vector-search test fixtures.

    Returns:
        Seeded context read model.
    """
    now = now_utc()
    model = ContextORM(
        kind=kind.value,
        title=title,
        summary=summary,
        content=content,
        content_format=ContextContentFormat.MARKDOWN.value,
        project=project,
        scope=scope.value,
        workspace_id=workspace_id,
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
        visibility=visibility.value,
        source_agent=source_agent,
        source_type=source_type.value,
        importance=importance.value,
        tags=[] if tags is None else tags,
        status=status.value,
        quality_score=quality_score,
        warnings=[] if warnings is None else warnings,
        restore_prompt=restore_prompt,
        context_metadata={} if context_metadata is None else context_metadata,
        created_at=now if created_at is None else created_at,
        updated_at=now if updated_at is None else updated_at,
        expires_at=None,
        access_count=0,
        is_archived=False,
    )
    session.add(model)
    await session.flush()

    markdown_chunks = list(chunk_markdown(title=title, content=content))
    embeddings = (
        embedding_provider.embed_documents([chunk.content for chunk in markdown_chunks])
        if embedding_provider is not None
        else [None for _ in markdown_chunks]
    )
    fingerprint = (
        None if embedding_provider is None else embedding_provider.fingerprint()
    )
    chunk_rows: list[ContextChunkORM] = []
    for chunk, embedding in zip(markdown_chunks, embeddings, strict=True):
        chunk_row = ContextChunkORM(
            context_id=model.id,
            chunk_index=chunk.chunk_index,
            heading=chunk.heading,
            content=chunk.content,
            token_count=chunk.token_count,
            content_hash=chunk.content_hash,
            embedding=None if embedding is None else vector_to_sqlite_json(embedding),
            embedding_model=None
            if embedding is None or embedding_provider is None
            else embedding_provider.model_name,
            embedding_dimensions=None
            if embedding is None or embedding_provider is None
            else embedding_provider.dimensions,
            embedding_provider=None if fingerprint is None else fingerprint.provider,
            embedding_provider_version=None
            if fingerprint is None
            else fingerprint.provider_version,
            embedding_pooling_mode=None
            if fingerprint is None
            else fingerprint.pooling_mode,
            embedding_normalize=None if fingerprint is None else fingerprint.normalize,
            embedding_fingerprint_key=None
            if fingerprint is None
            else fingerprint.key(),
            embedding_fingerprint_json=None
            if fingerprint is None
            else fingerprint.snapshot_payload(indexed_at=now),
            embedding_indexed_at=None if fingerprint is None else now,
            chunk_metadata=chunk.metadata,
            created_at=now,
        )
        chunk_rows.append(chunk_row)
    session.add_all(chunk_rows)
    await session.flush()

    await ensure_context_chunk_fts_table(session=session)
    for chunk_row in chunk_rows:
        await session.execute(
            text(INSERT_CONTEXT_CHUNK_FTS_SQL),
            {
                "chunk_id": chunk_row.id,
                "context_id": model.id,
                "title": model.title,
                "summary": model.summary,
                "content": chunk_row.content,
                "kind": model.kind,
                "project": model.project or "",
                "source_agent": model.source_agent,
                "tags": " ".join(str(tag) for tag in model.tags),
                "scope": model.scope,
                "workspace_id": model.workspace_id or "",
                "agent_id": model.agent_id or "",
                "user_id": model.user_id or "",
                "session_id": model.session_id or "",
                "heading": chunk_row.heading or "",
            },
        )
    return map_context_row(model)
