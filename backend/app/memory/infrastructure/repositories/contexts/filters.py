"""Filter builders for Context Vault repository queries."""

from __future__ import annotations

from app.memory.domain.event_enum.context_enums import ContextKind, ContextScope
from app.memory.infrastructure.models.context_models import ContextORM
from sqlalchemy import Select, bindparam, exists, func, select


def filtered_context_statement(
    *,
    kind: ContextKind | None,
    project: str | None,
    scope: ContextScope | None,
    workspace_id: str | None,
    agent_id: str | None,
    user_id: str | None,
    session_id: str | None,
    source_agent: str | None,
    tag: str | None,
    include_archived: bool,
) -> Select[tuple[ContextORM]]:
    """Build a filtered context query statement.

    Args:
        kind: Optional context kind filter.
        project: Optional project filter.
        scope: Optional scope filter.
        workspace_id: Optional workspace filter.
        agent_id: Optional agent filter.
        user_id: Optional user filter.
        session_id: Optional session filter.
        source_agent: Optional source-agent filter.
        tag: Optional tag filter.
        include_archived: Whether archived entries are included.

    Returns:
        SQLAlchemy select statement with requested filters applied.
    """
    statement = select(ContextORM)
    if not include_archived:
        statement = statement.where(ContextORM.is_archived.is_(False))
    if kind is not None:
        statement = statement.where(ContextORM.kind == kind.value)
    if project is not None:
        statement = statement.where(ContextORM.project == project)
    if scope is not None:
        statement = statement.where(ContextORM.scope == scope.value)
    if workspace_id is not None:
        statement = statement.where(ContextORM.workspace_id == workspace_id)
    if agent_id is not None:
        statement = statement.where(ContextORM.agent_id == agent_id)
    if user_id is not None:
        statement = statement.where(ContextORM.user_id == user_id)
    if session_id is not None:
        statement = statement.where(ContextORM.session_id == session_id)
    if source_agent is not None:
        statement = statement.where(ContextORM.source_agent == source_agent)
    if tag is not None:
        tag_values = func.json_each(ContextORM.tags).table_valued("value")
        statement = statement.where(
            exists(
                select(1)
                .select_from(tag_values)
                .where(tag_values.c.value == bindparam("context_tag", tag))
            )
        )
    return statement
