"""Immutable persistence contracts for local MCP OAuth state."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from app.shared.types.extra_types import JSONValue


class LocalOAuthTokenKind(StrEnum):
    """Persisted opaque token categories."""

    ACCESS = "access"
    REFRESH = "refresh"


@dataclass(frozen=True, slots=True)
class LocalOAuthPairingCode:
    """One-time local approval code returned only at creation time."""

    code: str
    expires_at: int


@dataclass(frozen=True, slots=True)
class LocalOAuthClientRecord:
    """Persisted dynamic OAuth client registration."""

    client_id: str
    client_secret_ciphertext: str | None
    metadata: Mapping[str, JSONValue]
    issued_at: int
    secret_expires_at: int | None


@dataclass(frozen=True, slots=True)
class LocalOAuthAuthorizationRequestRecord:
    """Pending operator-approved OAuth authorization request."""

    request_id: str
    client_id: str
    client_name: str | None
    state: str | None
    scopes: tuple[str, ...]
    code_challenge: str
    redirect_uri: str
    redirect_uri_provided_explicitly: bool
    resource: str
    expires_at: int
    approval_attempts: int
    consumed_at: int | None


@dataclass(frozen=True, slots=True)
class LocalOAuthAuthorizationCodeRecord:
    """One-time authorization code state loaded by its opaque raw value."""

    code: str
    client_id: str
    scopes: tuple[str, ...]
    code_challenge: str
    redirect_uri: str
    redirect_uri_provided_explicitly: bool
    resource: str
    expires_at: int


@dataclass(frozen=True, slots=True)
class LocalOAuthTokenRecord:
    """Active opaque OAuth token state loaded by its raw value."""

    token: str
    token_kind: LocalOAuthTokenKind
    family_id: str
    client_id: str
    scopes: tuple[str, ...]
    resource: str
    expires_at: int
