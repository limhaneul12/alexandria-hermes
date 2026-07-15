"""Authentication contracts for the public MCP HTTP boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final


class McpAuthMode(StrEnum):
    """Supported authentication modes for the public MCP endpoint."""

    NONE = "none"
    OAUTH2 = "oauth2"


class JwtAlgorithm(StrEnum):
    """JWT algorithms accepted by the MCP OAuth resource server."""

    RS256 = "RS256"


class OAuthBearerErrorCode(StrEnum):
    """OAuth bearer challenge error codes used at the MCP boundary."""

    INVALID_REQUEST = "invalid_request"
    INVALID_TOKEN = "invalid_token"
    INSUFFICIENT_SCOPE = "insufficient_scope"


MCP_OAUTH_PROTECTED_RESOURCE_PATH: Final[str] = "/.well-known/oauth-protected-resource"


@dataclass(frozen=True)
class McpHttpAuthResult:
    """Authorization result for one MCP HTTP request."""

    allowed: bool
    status_code: int = 200
    detail: str = "ok"
    headers: Mapping[str, str] = MappingProxyType({})
