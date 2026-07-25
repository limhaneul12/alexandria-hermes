"""Compatibility facade for memory reconciliation request schema."""

from __future__ import annotations

from app.memory.interface.schemas.reconciliation.memory_reconciliation_candidate_request_schema import (
    CanonicalClaimQualifierRequest,
    CanonicalClaimRequest,
    MemoryCandidateRequest,
    MemoryReconciliationApplyRequest,
    MemoryReconciliationPreviewHttpRequest,
    MemorySourceReferenceRequest,
)
from app.memory.interface.schemas.reconciliation.memory_reconciliation_conflict_request_schema import (
    MemoryConflictResolutionRequest,
)
from app.memory.interface.schemas.reconciliation.memory_reconciliation_temporal_request_schema import (
    MemoryTemporalRecallHttpRequest,
)

__all__ = [
    "CanonicalClaimQualifierRequest",
    "CanonicalClaimRequest",
    "MemoryCandidateRequest",
    "MemoryConflictResolutionRequest",
    "MemoryReconciliationApplyRequest",
    "MemoryReconciliationPreviewHttpRequest",
    "MemorySourceReferenceRequest",
    "MemoryTemporalRecallHttpRequest",
]
