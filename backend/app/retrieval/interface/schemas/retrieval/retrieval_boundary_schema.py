"""Schemas exposing retrieval role boundaries."""

from __future__ import annotations

from app.retrieval.domain.event_enum.retrieval_boundary_enums import RetrievalMode
from app.shared.schemas.common_schemas import StrictRootSchemaModel, StrictSchemaModel


class RetrievalModeResponse(StrictSchemaModel):
    """One retrieval mode exposed for agent/UI guardrails."""

    mode: RetrievalMode
    description: str
    default_endpoint: str
    returns_full_content: bool
    uses_librarian: bool


class RetrievalModeResponseList(StrictRootSchemaModel[list[RetrievalModeResponse]]):
    """Root response for retrieval mode descriptions."""
