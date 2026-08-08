"""Typed compact response contracts for Obsidian MCP search."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.shared.types.extra_types import JSONObject, JSONValue


class VaultSearchBackendNote(BaseModel):
    """Validated subset of one backend Obsidian note search payload."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str
    alexandria_type: str
    path: str
    title: str
    status: str
    tags: list[str] = Field(default_factory=list)
    project: str | None = None
    content_hash: str | None = None
    index_status: str | None = None
    wikilink: str | None = None


class VaultSearchBackendHit(BaseModel):
    """Validated backend search hit used by the MCP compaction boundary."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    note: VaultSearchBackendNote
    excerpt: str
    score: float
    chunk_id: str | None = None
    heading_path: str | None = None


class VaultSearchBackendResponse(BaseModel):
    """Validated backend search response before MCP compaction."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    items: list[VaultSearchBackendHit] = Field(default_factory=list)
    total: int = 0


class VaultSearchToolNote(BaseModel):
    """Agent-facing note metadata returned by compact vault search."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    note_id: str
    alexandria_type: str
    path: str
    title: str
    status: str
    tags: list[str] = Field(default_factory=list)
    project: str | None = None
    content_hash: str | None = None
    index_status: str | None = None
    wikilink: str | None = None

    @classmethod
    def from_backend(cls, note: VaultSearchBackendNote) -> VaultSearchToolNote:
        """Create compact agent-facing note metadata.

        Args:
            note: Validated backend note search payload.

        Returns:
            Compact MCP note metadata without body or frontmatter.
        """
        return cls(
            note_id=note.id,
            alexandria_type=note.alexandria_type,
            path=note.path,
            title=note.title,
            status=note.status,
            tags=note.tags,
            project=note.project,
            content_hash=note.content_hash,
            index_status=note.index_status,
            wikilink=note.wikilink,
        )

    def to_payload(self) -> JSONObject:
        """Serialize compact note metadata to the JSON boundary.

        Returns:
            JSON object safe for the MCP response.
        """
        return {
            "note_id": self.note_id,
            "alexandria_type": self.alexandria_type,
            "path": self.path,
            "title": self.title,
            "status": self.status,
            "tags": self.tags,
            "project": self.project,
            "content_hash": self.content_hash,
            "index_status": self.index_status,
            "wikilink": self.wikilink,
        }


class VaultSearchToolHit(BaseModel):
    """One compact note-level MCP vault search result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    note: VaultSearchToolNote
    excerpt: str
    score: float
    chunk_id: str | None = None
    heading_path: str | None = None

    @classmethod
    def from_backend(cls, hit: VaultSearchBackendHit) -> VaultSearchToolHit:
        """Create one compact MCP search hit.

        Args:
            hit: Validated backend search hit.

        Returns:
            Compact hit retaining only note metadata and the matched excerpt.
        """
        return cls(
            note=VaultSearchToolNote.from_backend(hit.note),
            excerpt=hit.excerpt,
            score=hit.score,
            chunk_id=hit.chunk_id,
            heading_path=hit.heading_path,
        )

    def to_payload(self) -> JSONObject:
        """Serialize one compact search hit.

        Returns:
            JSON object safe for the MCP response.
        """
        return {
            "note": self.note.to_payload(),
            "excerpt": self.excerpt,
            "score": self.score,
            "chunk_id": self.chunk_id,
            "heading_path": self.heading_path,
        }


def compact_vault_search_response(value: JSONValue) -> JSONObject:
    """Validate and compact one backend vault search response.

    Args:
        value: Raw JSON response returned by the backend search endpoint.

    Returns:
        Note-level MCP response without full Markdown bodies or frontmatter.
    """
    backend = VaultSearchBackendResponse.model_validate(value)
    seen_note_ids: set[str] = set()
    items: list[JSONObject] = []
    for item in backend.items:
        if item.note.id in seen_note_ids:
            continue
        seen_note_ids.add(item.note.id)
        items.append(VaultSearchToolHit.from_backend(item).to_payload())
    return {
        "items": items,
        "total": len(items),
    }
