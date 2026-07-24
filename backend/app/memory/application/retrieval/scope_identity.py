"""Compatibility exports for validated Context recall scope identities."""

from __future__ import annotations

from app.memory.domain.contracts.context_recall_contracts import (
    ScopeIdentity,
    validated_scope_identity,
)

__all__ = ["ScopeIdentity", "validated_scope_identity"]
