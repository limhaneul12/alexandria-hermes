"""Context Vault enum contracts."""

from __future__ import annotations

from enum import StrEnum


class ContextKind(StrEnum):
    """Kinds of durable context stored by agents and humans."""

    HANDOFF = "HANDOFF"
    DECISION = "DECISION"
    BUG_ROOT_CAUSE = "BUG_ROOT_CAUSE"
    PLAN = "PLAN"
    COMPACT = "COMPACT"
    RESEARCH = "RESEARCH"
    USAGE = "USAGE"
    MEMORY = "MEMORY"


class ContextSourceType(StrEnum):
    """Source category for a captured context."""

    AGENT = "AGENT"
    USER = "USER"
    SYSTEM = "SYSTEM"
    IMPORTED = "IMPORTED"


class ContextScope(StrEnum):
    """Recall-routing scope for durable memory."""

    GLOBAL = "GLOBAL"
    PROJECT = "PROJECT"
    AGENT = "AGENT"
    SESSION = "SESSION"
    USER = "USER"


class ContextImportance(StrEnum):
    """Importance level used for recall ranking and filtering."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ContextStorageStatus(StrEnum):
    """Context lint/save statuses returned by the harness."""

    SAVED = "SAVED"
    SAVED_WITH_WARNINGS = "SAVED_WITH_WARNINGS"
    REDACTED_AND_SAVED = "REDACTED_AND_SAVED"
    BLOCKED_SECRET_RISK = "BLOCKED_SECRET_RISK"
    PENDING_REVIEW = "PENDING_REVIEW"


class ContextContentFormat(StrEnum):
    """Supported context content formats."""

    MARKDOWN = "MARKDOWN"
    TEXT = "TEXT"


class ContextAccessActorType(StrEnum):
    """Actor categories for Context Vault access events."""

    UI = "UI"
    AGENT = "AGENT"
    LIBRARIAN = "LIBRARIAN"
    SYSTEM = "SYSTEM"


class ContextAccessMethod(StrEnum):
    """How a Context Vault entry was accessed."""

    DETAIL_VIEW = "DETAIL_VIEW"
    RECALL = "RECALL"
    RAG_SEARCH = "RAG_SEARCH"
    MCP_TOOL = "MCP_TOOL"


class RagStrategy(StrEnum):
    """Context retrieval strategies exposed by RAG search."""

    FTS_ONLY = "FTS_ONLY"
    VECTOR_ONLY = "VECTOR_ONLY"
    HYBRID = "HYBRID"


class RagHealthState(StrEnum):
    """Health states for retriever dependencies."""

    HEALTHY = "HEALTHY"
    REINDEX_REQUIRED = "REINDEX_REQUIRED"
    DEGRADED = "DEGRADED"
    DISABLED = "DISABLED"
