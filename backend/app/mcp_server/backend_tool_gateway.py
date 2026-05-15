"""MCP tool gateway backed exclusively by Alexandria-Hermes HTTP APIs."""

from __future__ import annotations

from typing import cast
from urllib.parse import quote

from app.library.domain.event_enum.context_enums import (
    ContextImportance,
    ContextKind,
    ContextSourceType,
    RagStrategy,
)
from app.library.domain.event_enum.item_enums import ItemStatus
from app.library.domain.event_enum.skill_enums import RiskLevel
from app.library.interface.schemas.context.context_schema import (
    ContextCaptureRequest,
    ContextPrepareCompactRequest,
    ContextSearchRequest,
)
from app.library.interface.schemas.librarian.librarian_ops_schemas import (
    CreateCandidateRequest,
)
from app.library.interface.schemas.skill.request_schemas import AgentSubmitSkillRequest
from app.mcp_server.backend_api_client import AlexandriaApiClient
from app.mcp_server.mcp_protocol_enums import McpContextTag
from app.shared.types.extra_types import JSONObject, JSONValue
from pydantic import BaseModel

DEFAULT_CONTEXT_SEARCH_LIMIT = 5
DEFAULT_CONTEXT_SEARCH_STRATEGY = RagStrategy.HYBRID
DEFAULT_CAPTURE_KIND = ContextKind.HANDOFF
DEFAULT_SOURCE_AGENT = "Hermes"
DEFAULT_CAPTURE_SOURCE_TYPE = ContextSourceType.AGENT
DEFAULT_CAPTURE_IMPORTANCE = ContextImportance.MEDIUM
DEFAULT_SKILL_PROVIDER_ID = "hermes-self-acquisition"
DEFAULT_CANDIDATE_AUTHOR = "Hermes"


async def alexandria_search(
    client: AlexandriaApiClient,
    query: str,
    limit: int = DEFAULT_CONTEXT_SEARCH_LIMIT,
    strategy: RagStrategy = DEFAULT_CONTEXT_SEARCH_STRATEGY,
    project: str | None = None,
    kind: ContextKind | None = None,
) -> JSONValue:
    """Search Context Vault and return a Context Pack.

    Args:
        client: Backend HTTP client.
        query: Search query.
        limit: Maximum matches.
        strategy: Retrieval strategy.
        project: Optional project filter.
        kind: Optional context kind filter.

    Returns:
        Backend Context Pack response.
    """
    request = ContextSearchRequest(
        query=query,
        strategy=strategy,
        limit=_bounded_search_limit(limit),
        project=project,
        kind=kind,
    )
    payload = _schema_payload(request)
    response = await client.post("/library/contexts/search", payload)
    return response


async def alexandria_recall_context(
    client: AlexandriaApiClient,
    query: str,
    limit: int = DEFAULT_CONTEXT_SEARCH_LIMIT,
    project: str | None = None,
    kind: ContextKind | None = None,
) -> JSONValue:
    """Recall durable context with default hybrid retrieval.

    Args:
        client: Backend HTTP client.
        query: Search query.
        limit: Maximum matches.
        project: Optional project filter.
        kind: Optional context kind filter.

    Returns:
        Backend Context Pack response.
    """
    response = await alexandria_search(
        client,
        query,
        limit,
        DEFAULT_CONTEXT_SEARCH_STRATEGY,
        project,
        kind,
    )
    return response


async def alexandria_rag_context(
    client: AlexandriaApiClient,
    query: str,
    strategy: RagStrategy = DEFAULT_CONTEXT_SEARCH_STRATEGY,
    limit: int = DEFAULT_CONTEXT_SEARCH_LIMIT,
) -> JSONValue:
    """Retrieve a RAG Context Pack with explicit strategy.

    Args:
        client: Backend HTTP client.
        query: Search query.
        strategy: Retrieval strategy.
        limit: Maximum matches.

    Returns:
        Backend Context Pack response.
    """
    response = await alexandria_search(client, query, limit, strategy)
    return response


async def alexandria_capture_context(
    client: AlexandriaApiClient,
    title: str,
    content: str,
    kind: ContextKind = DEFAULT_CAPTURE_KIND,
    summary: str | None = None,
    project: str | None = None,
    source_agent: str = DEFAULT_SOURCE_AGENT,
    source_type: ContextSourceType = DEFAULT_CAPTURE_SOURCE_TYPE,
) -> JSONValue:
    """Capture context through the backend Context Vault API.

    Args:
        client: Backend HTTP client.
        title: Context title.
        content: Markdown content.
        kind: Context kind.
        summary: Optional summary.
        project: Optional project scope.
        source_agent: Producing agent name.
        source_type: Source category for agent-authored context.

    Returns:
        Stored context response.
    """
    request = ContextCaptureRequest(
        kind=kind,
        title=title,
        content=content,
        summary=summary,
        project=project,
        source_agent=source_agent,
        source_type=source_type,
        importance=DEFAULT_CAPTURE_IMPORTANCE,
        expires_at=None,
        metadata={},
        tags=[McpContextTag.MCP.value, McpContextTag.CAPTURE.value],
    )
    payload = _schema_payload(request)
    response = await client.post("/library/contexts/capture", payload)
    return response


async def alexandria_prepare_compact(
    client: AlexandriaApiClient,
    current_goal: str,
    completed: list[str] | None = None,
    in_progress: list[str] | None = None,
    key_decisions: list[str] | None = None,
    next_actions: list[str] | None = None,
    risks: list[str] | None = None,
    project: str | None = None,
    source_agent: str = DEFAULT_SOURCE_AGENT,
) -> JSONValue:
    """Prepare and save a compact handoff context.

    Args:
        client: Backend HTTP client.
        current_goal: Current work goal.
        completed: Completed bullets.
        in_progress: Active work bullets.
        key_decisions: Decision bullets.
        next_actions: Next action bullets.
        risks: Risk bullets.
        project: Optional project scope.
        source_agent: Producing agent name.

    Returns:
        Stored compact context response.
    """
    request = ContextPrepareCompactRequest(
        project=project,
        source_agent=source_agent,
        current_goal=current_goal,
        completed=_items_or_empty(completed),
        in_progress=_items_or_empty(in_progress),
        key_decisions=_items_or_empty(key_decisions),
        next_actions=_items_or_empty(next_actions),
        risks=_items_or_empty(risks),
    )
    payload = _schema_payload(request)
    response = await client.post("/library/contexts/prepare-compact", payload)
    return response


async def alexandria_archive_context(
    client: AlexandriaApiClient, context_id: str
) -> JSONValue:
    """Archive a context without exposing hard delete.

    Args:
        client: Backend HTTP client.
        context_id: Context identifier.

    Returns:
        Archived context response.
    """
    response = await client.post(
        f"/library/contexts/{_path_segment(context_id)}/archive", {}
    )
    return response


async def alexandria_rag_status(client: AlexandriaApiClient) -> JSONValue:
    """Read Context RAG dependency status.

    Args:
        client: Backend HTTP client.

    Returns:
        RAG health response.
    """
    response = await client.get("/library/contexts/rag/status")
    return response


async def alexandria_get_skill(client: AlexandriaApiClient, item_id: str) -> JSONValue:
    """Read one skill by id.

    Args:
        client: Backend HTTP client.
        item_id: Skill item identifier.

    Returns:
        Skill item response.
    """
    response = await client.get(f"/skills/{_path_segment(item_id)}")
    return response


async def alexandria_get_prompt(client: AlexandriaApiClient, item_id: str) -> JSONValue:
    """Read one prompt by id.

    Args:
        client: Backend HTTP client.
        item_id: Prompt item identifier.

    Returns:
        Prompt item response.
    """
    response = await client.get(f"/prompts/{_path_segment(item_id)}")
    return response


async def alexandria_request_skill_acquisition(
    client: AlexandriaApiClient,
    prompt: str,
    provider_id: str = DEFAULT_SKILL_PROVIDER_ID,
    category_id: str | None = None,
) -> JSONValue:
    """Request a draft skill candidate from the librarian workflow.

    Args:
        client: Backend HTTP client.
        prompt: Missing-capability description.
        provider_id: Librarian provider identifier or self-acquisition marker.
        category_id: Optional category identifier.

    Returns:
        Draft skill candidate response.
    """
    request = CreateCandidateRequest(
        provider_id=provider_id,
        prompt=prompt,
        category_id=category_id,
    )
    payload = _schema_payload(request)
    response = await client.post("/librarian/create-skill-candidate", payload)
    return response


async def alexandria_submit_skill_candidate(
    client: AlexandriaApiClient,
    title: str,
    purpose: str,
    content: str,
    summary: str | None = None,
    created_by_name: str = DEFAULT_CANDIDATE_AUTHOR,
) -> JSONValue:
    """Submit a Hermes-authored skill candidate.

    Args:
        client: Backend HTTP client.
        title: Candidate title.
        purpose: Candidate purpose.
        content: Candidate Markdown content.
        summary: Optional summary.
        created_by_name: Producing agent name.

    Returns:
        Stored skill response.
    """
    request = AgentSubmitSkillRequest(
        title=title,
        purpose=purpose,
        summary=summary,
        content=content,
        category_id=None,
        tags=[McpContextTag.HERMES.value, McpContextTag.CANDIDATE.value],
        input_schema={},
        output_schema={},
        usage_example=None,
        required_tools=[],
        risk_level=RiskLevel.LOW,
        version="1.0.0",
        created_by_name=created_by_name,
        activate=False,
        status=ItemStatus.DRAFT,
    )
    payload = _schema_payload(request)
    response = await client.post("/skills/submit-by-agent", payload)
    return response


def _schema_payload(schema: BaseModel) -> JSONObject:
    payload = cast(JSONObject, schema.model_dump(mode="json", exclude_none=True))
    return payload


def _bounded_search_limit(limit: int) -> int:
    bounded_limit = min(max(int(limit), 1), 50)
    return bounded_limit


def _path_segment(value: str) -> str:
    """Return one URL-safe path segment.

    Args:
        value: Untrusted path parameter.

    Returns:
        Percent-encoded path segment safe for backend URL construction.
    """
    return quote(value, safe="")


def _items_or_empty(items: list[str] | None) -> list[str]:
    """Normalize optional bullet lists for compact handoff payloads.

    Args:
        items: Caller-provided list or omitted value.

    Returns:
        Original list or an empty list when omitted.
    """
    if items is None:
        return []
    return items
