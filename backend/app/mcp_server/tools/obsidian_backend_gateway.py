"""Obsidian search, note, graph, and librarian MCP HTTP gateway functions."""

from __future__ import annotations

from app.mcp_server.backend_api_client import AlexandriaApiClient
from app.mcp_server.tools.backend_gateway_policy import (
    DEFAULT_CONTEXT_SEARCH_LIMIT,
    _bounded_search_limit,
    _items_or_empty,
    _path_segment,
)
from app.obsidian.application.notes.frontmatter_metadata_normalization import (
    normalize_known_frontmatter_metadata,
    normalize_string_collection,
)
from app.shared.types.extra_types import JSONObject, JSONValue


async def alexandria_search_vault(
    client: AlexandriaApiClient,
    query: str,
    limit: int = DEFAULT_CONTEXT_SEARCH_LIMIT,
    alexandria_type: str | None = None,
    project: str | None = None,
    tags: list[str] | None = None,
) -> JSONValue:
    """Search Alexandria-managed Obsidian Markdown notes.

    Args:
        client: Backend HTTP client.
        query: Search query.
        limit: Maximum matches.
        alexandria_type: Optional managed note type.
        project: Optional project filter.
        tags: Optional tag filters.

    Returns:
        Backend search response.
    """
    payload: JSONObject = {
        "query": query,
        "limit": _bounded_search_limit(limit),
        "tags": _items_or_empty(tags),
    }
    if alexandria_type is not None:
        payload["alexandria_type"] = alexandria_type
    if project is not None:
        payload["project"] = project
    return await client.post("/obsidian/search", payload)


async def alexandria_read_note(
    client: AlexandriaApiClient,
    note_id: str | None = None,
    path: str | None = None,
) -> JSONValue:
    """Read one Alexandria-managed Obsidian note by id or path.

    Args:
        client: Backend HTTP client.
        note_id: Stable note id.
        path: Vault-relative path.

    Returns:
        Backend note response.
    """
    if path is not None:
        return await client.get("/obsidian/notes/by-path", params={"path": path})
    if note_id is None:
        raise ValueError("note_id or path is required")
    return await client.get(f"/obsidian/notes/{_path_segment(note_id)}")


async def alexandria_check_path_exists(
    client: AlexandriaApiClient,
    path: str,
) -> JSONValue:
    """Check one exact managed path without fuzzy retrieval.

    Args:
        client: Value supplied to alexandria_check_path_exists.
        path: Value supplied to alexandria_check_path_exists.

    Returns:
        Result produced by alexandria_check_path_exists.
    """
    return await client.get("/obsidian/notes/check-path", params={"path": path})


async def alexandria_resolve_canonical_identity(
    client: AlexandriaApiClient,
    project: str,
    report: str,
    date: str,
    entity: str,
    edition: str | None = None,
) -> JSONValue:
    """Resolve a report identity through existing metadata and declared aliases.

    Args:
        client: Value supplied to alexandria_resolve_canonical_identity.
        project: Value supplied to alexandria_resolve_canonical_identity.
        report: Value supplied to alexandria_resolve_canonical_identity.
        date: Value supplied to alexandria_resolve_canonical_identity.
        entity: Value supplied to alexandria_resolve_canonical_identity.
        edition: Value supplied to alexandria_resolve_canonical_identity.

    Returns:
        Result produced by alexandria_resolve_canonical_identity.
    """
    payload: JSONObject = {
        "project": project,
        "report": report,
        "date": date,
        "entity": entity,
    }
    if edition is not None:
        payload["edition"] = edition
    return await client.post("/obsidian/notes/resolve-canonical-identity", payload)


async def alexandria_get_related_notes(
    client: AlexandriaApiClient,
    note_id: str | None = None,
    path: str | None = None,
    limit: int = DEFAULT_CONTEXT_SEARCH_LIMIT,
) -> JSONValue:
    """Read graph-related Obsidian notes by id or path.

    Args:
        client: Backend HTTP client.
        note_id: Stable note id.
        path: Vault-relative note path.
        limit: Maximum related notes.

    Returns:
        Backend related notes response.
    """
    bounded_limit = _bounded_search_limit(limit)
    if path is not None:
        return await client.get(
            "/obsidian/notes/by-path/related",
            params={"path": path, "limit": bounded_limit},
        )
    if note_id is None:
        raise ValueError("note_id or path is required")
    return await client.get(
        f"/obsidian/notes/{_path_segment(note_id)}/related",
        params={"limit": bounded_limit},
    )


async def alexandria_save_note(
    client: AlexandriaApiClient,
    title: str,
    body: str,
    alexandria_type: str,
    note_id: str | None = None,
    path: str | None = None,
    project: str | None = None,
    tags: list[str] | str | None = None,
    status: str = "active",
    source: str = "mcp",
    frontmatter: JSONObject | None = None,
) -> JSONValue:
    """Save one Alexandria-managed Obsidian Markdown note.

    Args:
        client: Backend HTTP client.
        title: Note title.
        body: Markdown body.
        alexandria_type: Managed note type.
        note_id: Optional stable id.
        path: Optional vault-relative path.
        project: Optional project.
        tags: Optional tags as an array or one string.
        status: Frontmatter lifecycle status.
        source: Frontmatter source marker.
        frontmatter: Optional extra frontmatter object.

    Returns:
        Backend saved note response.
    """
    normalized_frontmatter = {} if frontmatter is None else dict(frontmatter)
    normalize_known_frontmatter_metadata(normalized_frontmatter)
    payload: JSONObject = {
        "title": title,
        "body": body,
        "alexandria_type": alexandria_type,
        "tags": normalize_string_collection(tags),
        "status": status,
        "source": source,
        "frontmatter": normalized_frontmatter,
    }
    if note_id is not None:
        payload["id"] = note_id
    if path is not None:
        payload["path"] = path
    if project is not None:
        payload["project"] = project
    return await client.post("/obsidian/notes", payload)


async def alexandria_create_note(
    client: AlexandriaApiClient,
    title: str,
    body: str,
    alexandria_type: str,
    match_by: str,
    note_id: str | None = None,
    path: str | None = None,
    project: str | None = None,
    tags: list[str] | str | None = None,
    status: str = "active",
    source: str = "mcp",
    frontmatter: JSONObject | None = None,
    frontmatter_mode: str = "merge",
) -> JSONValue:
    """Create only, rejecting an existing exact id or path before mutation.

    Args:
        client: Value supplied to alexandria_create_note.
        title: Value supplied to alexandria_create_note.
        body: Value supplied to alexandria_create_note.
        alexandria_type: Value supplied to alexandria_create_note.
        match_by: Value supplied to alexandria_create_note.
        note_id: Value supplied to alexandria_create_note.
        path: Value supplied to alexandria_create_note.
        project: Value supplied to alexandria_create_note.
        tags: Value supplied to alexandria_create_note.
        status: Value supplied to alexandria_create_note.
        source: Value supplied to alexandria_create_note.
        frontmatter: Value supplied to alexandria_create_note.
        frontmatter_mode: Value supplied to alexandria_create_note.

    Returns:
        Result produced by alexandria_create_note.
    """
    return await _alexandria_write_note(
        client,
        endpoint="/obsidian/notes/create",
        title=title,
        body=body,
        alexandria_type=alexandria_type,
        match_by=match_by,
        note_id=note_id,
        path=path,
        project=project,
        tags=tags,
        status=status,
        source=source,
        frontmatter=frontmatter,
        frontmatter_mode=frontmatter_mode,
    )


async def alexandria_update_note(
    client: AlexandriaApiClient,
    title: str,
    body: str,
    alexandria_type: str,
    match_by: str,
    note_id: str | None = None,
    path: str | None = None,
    project: str | None = None,
    tags: list[str] | str | None = None,
    status: str | None = None,
    source: str | None = None,
    frontmatter: JSONObject | None = None,
    frontmatter_mode: str = "merge",
    expected_content_hash: str | None = None,
) -> JSONValue:
    """Update an existing exact id or path without moving it implicitly.

    Args:
        client: Value supplied to alexandria_update_note.
        title: Value supplied to alexandria_update_note.
        body: Value supplied to alexandria_update_note.
        alexandria_type: Value supplied to alexandria_update_note.
        match_by: Value supplied to alexandria_update_note.
        note_id: Value supplied to alexandria_update_note.
        path: Value supplied to alexandria_update_note.
        project: Value supplied to alexandria_update_note.
        tags: Value supplied to alexandria_update_note.
        status: Value supplied to alexandria_update_note.
        source: Value supplied to alexandria_update_note.
        frontmatter: Value supplied to alexandria_update_note.
        frontmatter_mode: Value supplied to alexandria_update_note.
        expected_content_hash: Value supplied to alexandria_update_note.

    Returns:
        Result produced by alexandria_update_note.
    """
    return await _alexandria_write_note(
        client,
        endpoint="/obsidian/notes/update",
        title=title,
        body=body,
        alexandria_type=alexandria_type,
        match_by=match_by,
        note_id=note_id,
        path=path,
        project=project,
        tags=tags,
        status=status,
        source=source,
        frontmatter=frontmatter,
        frontmatter_mode=frontmatter_mode,
        expected_content_hash=expected_content_hash,
    )


async def alexandria_upsert_note(
    client: AlexandriaApiClient,
    title: str,
    body: str,
    alexandria_type: str,
    match_by: str,
    note_id: str | None = None,
    path: str | None = None,
    project: str | None = None,
    tags: list[str] | str | None = None,
    status: str | None = None,
    source: str | None = None,
    frontmatter: JSONObject | None = None,
    frontmatter_mode: str = "merge",
    expected_content_hash: str | None = None,
) -> JSONValue:
    """Create or update by one exact selector, rejecting selector conflicts.

    Args:
        client: Value supplied to alexandria_upsert_note.
        title: Value supplied to alexandria_upsert_note.
        body: Value supplied to alexandria_upsert_note.
        alexandria_type: Value supplied to alexandria_upsert_note.
        match_by: Value supplied to alexandria_upsert_note.
        note_id: Value supplied to alexandria_upsert_note.
        path: Value supplied to alexandria_upsert_note.
        project: Value supplied to alexandria_upsert_note.
        tags: Value supplied to alexandria_upsert_note.
        status: Value supplied to alexandria_upsert_note.
        source: Value supplied to alexandria_upsert_note.
        frontmatter: Value supplied to alexandria_upsert_note.
        frontmatter_mode: Value supplied to alexandria_upsert_note.
        expected_content_hash: Value supplied to alexandria_upsert_note.

    Returns:
        Result produced by alexandria_upsert_note.
    """
    return await _alexandria_write_note(
        client,
        endpoint="/obsidian/notes/upsert",
        title=title,
        body=body,
        alexandria_type=alexandria_type,
        match_by=match_by,
        note_id=note_id,
        path=path,
        project=project,
        tags=tags,
        status=status,
        source=source,
        frontmatter=frontmatter,
        frontmatter_mode=frontmatter_mode,
        expected_content_hash=expected_content_hash,
    )


async def _alexandria_write_note(
    client: AlexandriaApiClient,
    *,
    endpoint: str,
    title: str,
    body: str,
    alexandria_type: str,
    match_by: str,
    note_id: str | None,
    path: str | None,
    project: str | None,
    tags: list[str] | str | None,
    status: str | None,
    source: str | None,
    frontmatter: JSONObject | None,
    frontmatter_mode: str,
    expected_content_hash: str | None = None,
) -> JSONValue:
    payload: JSONObject = {
        "title": title,
        "body": body,
        "alexandria_type": alexandria_type,
        "match_by": match_by,
        "frontmatter_mode": frontmatter_mode,
    }
    if tags is not None:
        payload["tags"] = normalize_string_collection(tags)
    if status is not None:
        payload["status"] = status
    if source is not None:
        payload["source"] = source
    if frontmatter is not None:
        normalized_frontmatter = dict(frontmatter)
        normalize_known_frontmatter_metadata(normalized_frontmatter)
        payload["frontmatter"] = normalized_frontmatter
    if note_id is not None:
        payload["id"] = note_id
    if path is not None:
        payload["path"] = path
    if project is not None:
        payload["project"] = project
    if expected_content_hash is not None:
        payload["expected_content_hash"] = expected_content_hash
    return await client.post(endpoint, payload)


async def alexandria_upsert_report_bundle(
    client: AlexandriaApiClient,
    idempotency_key: str,
    source: JSONObject,
    graph_owners: list[JSONObject],
    reindex: bool = True,
    verify_index_status: bool = True,
    verify_incoming_edges: bool = True,
    verify_duplicates: bool = True,
) -> JSONValue:
    """Run one retry-safe Source/owner/reindex/graph verification operation.

    Args:
        client: Value supplied to alexandria_upsert_report_bundle.
        idempotency_key: Value supplied to alexandria_upsert_report_bundle.
        source: Value supplied to alexandria_upsert_report_bundle.
        graph_owners: Value supplied to alexandria_upsert_report_bundle.
        reindex: Value supplied to alexandria_upsert_report_bundle.
        verify_index_status: Value supplied to alexandria_upsert_report_bundle.
        verify_incoming_edges: Value supplied to alexandria_upsert_report_bundle.
        verify_duplicates: Value supplied to alexandria_upsert_report_bundle.

    Returns:
        Result produced by alexandria_upsert_report_bundle.
    """
    normalized_source = dict(source)
    frontmatter = normalized_source.get("frontmatter")
    if isinstance(frontmatter, dict):
        normalized_frontmatter = dict(frontmatter)
        normalize_known_frontmatter_metadata(normalized_frontmatter)
        normalized_source["frontmatter"] = normalized_frontmatter
    payload: JSONObject = {
        "idempotency_key": idempotency_key,
        "source": normalized_source,
        "graph_owners": [dict(owner) for owner in graph_owners],
        "reindex": reindex,
        "verify": {
            "index_status": verify_index_status,
            "incoming_edges": verify_incoming_edges,
            "duplicates": verify_duplicates,
        },
    }
    return await client.post("/obsidian/report-bundles/upsert", payload)


async def alexandria_ask_obsidian_librarian(
    client: AlexandriaApiClient,
    query: str,
    active_note_path: str | None = None,
    selection: str | None = None,
    project: str | None = None,
    save_transcript: bool = False,
    preferred_alexandria_types: list[str] | None = None,
    delegate_to_librarian: bool = False,
    provider_id: str | None = None,
    profile_id: str | None = None,
) -> JSONValue:
    """Ask the Obsidian-aware Alexandria librarian.

    Args:
        client: Backend HTTP client.
        query: User question.
        active_note_path: Optional active note path from Obsidian.
        selection: Optional selected Markdown text.
        project: Optional project scope.
        save_transcript: Whether to persist a librarian_chat note.
        preferred_alexandria_types: Optional type filters.
        delegate_to_librarian: Whether to request provider delegation hooks.
        provider_id: Optional preferred provider id.
        profile_id: Optional preferred profile id.

    Returns:
        Backend librarian response.
    """
    payload: JSONObject = {
        "query": query,
        "save_transcript": save_transcript,
        "preferred_alexandria_types": _items_or_empty(preferred_alexandria_types),
        "delegate_to_librarian": delegate_to_librarian,
    }
    if active_note_path is not None:
        payload["active_note_path"] = active_note_path
    if selection is not None:
        payload["selection"] = selection
    if project is not None:
        payload["project"] = project
    if provider_id is not None:
        payload["provider_id"] = provider_id
    if profile_id is not None:
        payload["profile_id"] = profile_id
    return await client.post("/obsidian/librarian/ask", payload)
