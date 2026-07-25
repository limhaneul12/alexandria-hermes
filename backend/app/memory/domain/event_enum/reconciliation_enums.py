"""Memory reconciliation symbolic domain values."""

from __future__ import annotations

from enum import StrEnum


class MemoryRelationType(StrEnum):
    """Supported semantic and temporal relations between durable memories."""

    DUPLICATE = "DUPLICATE"
    SUPPORTS = "SUPPORTS"
    EXTENDS = "EXTENDS"
    CONTRADICTS = "CONTRADICTS"
    SUPERSEDES = "SUPERSEDES"
    UNRELATED = "UNRELATED"
    UNKNOWN = "UNKNOWN"


class MemoryDecisionSource(StrEnum):
    """Origin of one reconciliation relation decision."""

    DETERMINISTIC = "DETERMINISTIC"
    SEMANTIC = "SEMANTIC"
    LLM = "LLM"
    HUMAN = "HUMAN"


class MemoryClaimPolarity(StrEnum):
    """Whether one canonical claim affirms or denies its proposition."""

    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"


class MemoryConflictStatus(StrEnum):
    """Lifecycle state for a durable memory conflict set."""

    OPEN = "OPEN"
    REVIEWING = "REVIEWING"
    RESOLVED_KEEP_BOTH = "RESOLVED_KEEP_BOTH"
    RESOLVED_SUPERSEDED = "RESOLVED_SUPERSEDED"
    RESOLVED_MERGED = "RESOLVED_MERGED"
    RESOLVED_INVALID_SOURCE = "RESOLVED_INVALID_SOURCE"


class MemoryReconciliationStatus(StrEnum):
    """Lifecycle state for a reconciliation plan or execution."""

    PLANNED = "PLANNED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPLYING = "APPLYING"
    APPLIED = "APPLIED"
    PARTIAL_APPLY = "PARTIAL_APPLY"
    FAILED = "FAILED"


class MemoryReconciliationActionType(StrEnum):
    """Explicit state transitions proposed by a reconciliation plan."""

    CREATE_CONTEXT = "CREATE_CONTEXT"
    MERGE_EVIDENCE = "MERGE_EVIDENCE"
    CREATE_RELATION = "CREATE_RELATION"
    MARK_SUPERSEDED = "MARK_SUPERSEDED"
    CREATE_CONFLICT_SET = "CREATE_CONFLICT_SET"
    QUEUE_REVIEW = "QUEUE_REVIEW"
    PRESERVE_CANDIDATE = "PRESERVE_CANDIDATE"
    NOOP = "NOOP"


class MemoryReconciliationFailureCode(StrEnum):
    """Stable failure categories for reconciliation execution."""

    CANDIDATE_VALIDATION_FAILED = "CANDIDATE_VALIDATION_FAILED"
    CLAIM_EXTRACTION_FAILED = "CLAIM_EXTRACTION_FAILED"
    RECALL_FAILED = "RECALL_FAILED"
    CLASSIFICATION_FAILED = "CLASSIFICATION_FAILED"
    POLICY_BLOCKED = "POLICY_BLOCKED"
    CONTEXT_WRITE_FAILED = "CONTEXT_WRITE_FAILED"
    GRAPH_WRITE_FAILED = "GRAPH_WRITE_FAILED"
    LIFECYCLE_UPDATE_FAILED = "LIFECYCLE_UPDATE_FAILED"
    CONFLICT_WRITE_FAILED = "CONFLICT_WRITE_FAILED"
    READ_BACK_VERIFICATION_FAILED = "READ_BACK_VERIFICATION_FAILED"
    PARTIAL_APPLY = "PARTIAL_APPLY"


class MemoryTemporalRecallMode(StrEnum):
    """Temporal perspective applied to Context recall results."""

    CURRENT = "CURRENT"
    HISTORICAL = "HISTORICAL"
    ALL = "ALL"


class MemoryCompactFactCategory(StrEnum):
    """Reconciliation-aware fact buckets presented to Memory Compact."""

    CURRENT = "CURRENT"
    HISTORICAL = "HISTORICAL"
    OPEN_CONFLICT = "OPEN_CONFLICT"
    UNCERTAIN = "UNCERTAIN"
    SUPERSEDED = "SUPERSEDED"


class MemoryCompactSafetyIssue(StrEnum):
    """Stable Memory Compact defects detected before durable publication."""

    UNRESOLVED_CONTRADICTION_LEAKAGE = "UNRESOLVED_CONTRADICTION_LEAKAGE"
    TEMPORAL_STATE_COLLAPSE = "TEMPORAL_STATE_COLLAPSE"
    SUPERSEDED_FACT_PRESENTED_AS_CURRENT = "SUPERSEDED_FACT_PRESENTED_AS_CURRENT"
    UNSUPPORTED_MERGE = "UNSUPPORTED_MERGE"
    DUPLICATE_CLAIM_INFLATION = "DUPLICATE_CLAIM_INFLATION"
