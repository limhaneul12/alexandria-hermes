"""Pydantic contracts for MCP protocol payloads consumed by CLI checks."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.serialization.orjson_codec import loads_json
from app.shared.types.extra_types import JSONValue


class McpProtocolPayloadSchema(BaseModel):
    """Base schema for partial MCP protocol response validation."""

    model_config = ConfigDict(
        extra="ignore",
        frozen=True,
        use_enum_values=True,
        validate_default=True,
    )


class McpToolPayload(McpProtocolPayloadSchema):
    """Validated subset of an MCP tool descriptor."""

    name: str | None = None


class McpToolsResultPayload(McpProtocolPayloadSchema):
    """Validated subset of an MCP tools/list result."""

    tools: tuple[McpToolPayload, ...] = Field(default_factory=tuple)

    @field_validator("tools", mode="before")
    @classmethod
    def _filter_tool_objects(cls, value: object) -> object:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        return value


class McpToolsListResponsePayload(McpProtocolPayloadSchema):
    """Validated subset of an MCP tools/list JSON-RPC response."""

    result: McpToolsResultPayload = Field(default_factory=McpToolsResultPayload)


class McpSmokeStatusPayload(McpProtocolPayloadSchema):
    """Validated subset of the CLI MCP smoke result payload."""

    ok: bool = False


def decode_mcp_json_response(text: str) -> JSONValue:
    """Decode JSON or SSE-framed JSON from an MCP HTTP response.

    Args:
        text: Raw HTTP response text.

    Returns:
        JSON-compatible decoded response payload.
    """
    stripped = text.strip()
    if stripped.startswith("event:") or "\ndata:" in stripped:
        data_lines = [
            line.removeprefix("data:").strip()
            for line in stripped.splitlines()
            if line.startswith("data:")
        ]
        stripped = "\n".join(data_lines)
    return loads_json(stripped)


def mcp_tool_names(payload: JSONValue) -> set[str]:
    """Return tool names from an MCP tools/list response payload.

    Args:
        payload: Decoded MCP tools/list response payload.

    Returns:
        Set of exposed MCP tool names.
    """
    response = McpToolsListResponsePayload.model_validate(_object_or_empty(payload))
    return {tool.name for tool in response.result.tools if tool.name is not None}


def mcp_smoke_ok(payload: JSONValue) -> bool:
    """Return whether an MCP smoke result payload is healthy.

    Args:
        payload: CLI MCP smoke result payload.

    Returns:
        True when all required MCP tools are exposed.
    """
    return McpSmokeStatusPayload.model_validate(_object_or_empty(payload)).ok is True


def _object_or_empty(payload: JSONValue) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    return {}


class McpSmokeToolsResultPayload(McpProtocolPayloadSchema):
    """Output schema for CLI MCP tools/list smoke results."""

    ok: bool
    mcp_url: str
    required_tools: tuple[str, ...] = Field(default_factory=tuple)
    missing_tools: tuple[str, ...] = Field(default_factory=tuple)
    tool_count: int
