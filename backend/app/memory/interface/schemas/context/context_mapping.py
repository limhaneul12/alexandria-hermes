"""Context Vault schema payload mappers."""

from __future__ import annotations

from app.memory.application.context_lint import ContextLintResult
from app.memory.domain.entities.context_read_models import (
    ContextChunkRecord,
    ContextPack,
    ContextRecord,
    ContextSearchMatch,
    RagDependencyHealth,
)
from app.memory.domain.types.context_payload_types import (
    ContextChunkPayload,
    ContextLintPayload,
    ContextPackPayload,
    ContextPayload,
    ContextSearchMatchPayload,
    RagHealthPayload,
)


def context_payload(context: ContextRecord) -> ContextPayload:
    """Return an API payload for one stored context.

    Args:
        context: Stored context read model.

    Returns:
        Typed response payload for the context API boundary.
    """
    payload: ContextPayload = {
        "id": context.id,
        "kind": context.kind,
        "title": context.title,
        "summary": context.summary,
        "content": context.content,
        "content_format": context.content_format,
        "project": context.project,
        "scope": context.scope,
        "workspace_id": context.workspace_id,
        "agent_id": context.agent_id,
        "user_id": context.user_id,
        "session_id": context.session_id,
        "visibility": context.visibility,
        "source_agent": context.source_agent,
        "source_type": context.source_type,
        "importance": context.importance,
        "tags": context.tags,
        "status": context.status,
        "quality_score": context.quality_score,
        "warnings": context.warnings,
        "restore_prompt": context.restore_prompt,
        "metadata": context.context_metadata,
        "created_at": context.created_at,
        "updated_at": context.updated_at,
        "last_accessed_at": context.last_accessed_at,
        "expires_at": context.expires_at,
        "archived_at": context.archived_at,
        "access_count": context.access_count,
        "is_archived": context.is_archived,
    }
    return payload


def chunk_payload(chunk: ContextChunkRecord) -> ContextChunkPayload:
    """Return an API payload for one stored context chunk.

    Args:
        chunk: Stored context chunk read model.

    Returns:
        Typed response payload for the context chunk API boundary.
    """
    payload: ContextChunkPayload = {
        "id": chunk.id,
        "context_id": chunk.context_id,
        "chunk_index": chunk.chunk_index,
        "heading": chunk.heading,
        "content": chunk.content,
        "token_count": chunk.token_count,
        "content_hash": chunk.content_hash,
        "metadata": chunk.chunk_metadata,
        "created_at": chunk.created_at,
    }
    return payload


def lint_payload(result: ContextLintResult) -> ContextLintPayload:
    """Return an API payload for a Context Harness lint result.

    Args:
        result: Context Harness lint result.

    Returns:
        Typed response payload for the context lint API boundary.
    """
    payload: ContextLintPayload = {
        "ok": result.ok,
        "status": result.status,
        "score": result.score,
        "errors": result.errors,
        "warnings": result.warnings,
        "suggestions": result.suggestions,
        "redacted_content": result.redacted_content,
        "redaction_report": result.redaction_report,
        "save_suggestion": result.save_suggestion,
        "normalized": result.normalized,
    }
    return payload


def match_payload(match: ContextSearchMatch) -> ContextSearchMatchPayload:
    """Return an API payload for one context search match.

    Args:
        match: Context search match read model.

    Returns:
        Typed response payload for one retrieved match.
    """
    payload: ContextSearchMatchPayload = {
        "context": context_payload(match.context),
        "chunk": chunk_payload(match.chunk),
        "score": match.score,
        "fts_score": match.fts_score,
        "vector_score": match.vector_score,
        "why_retrieved": match.why_retrieved,
    }
    return payload


def pack_payload(pack: ContextPack) -> ContextPackPayload:
    """Return an API payload for a RAG Context Pack.

    Args:
        pack: Context Pack read model.

    Returns:
        Typed response payload for the RAG Context Pack API boundary.
    """
    payload: ContextPackPayload = {
        "query": pack.query,
        "strategy": pack.strategy,
        "effective_strategy": pack.effective_strategy,
        "warnings": pack.warnings,
        "recall_scopes": pack.recall_scopes,
        "matches": [match_payload(match) for match in pack.matches],
        "context_pack": pack.context_pack,
    }
    return payload


def health_payload(health: RagDependencyHealth) -> RagHealthPayload:
    """Return an API payload for RAG dependency health.

    Args:
        health: RAG dependency health read model.

    Returns:
        Typed response payload for RAG dependency health.
    """
    payload: RagHealthPayload = {
        "fts": health.fts,
        "vector": health.vector,
        "embedding": health.embedding,
        "default_strategy": health.default_strategy,
        "model_name": health.model_name,
        "dimensions": health.dimensions,
        "warnings": health.warnings,
    }
    return payload
