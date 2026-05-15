"""Internal contracts for librarian OAuth lifecycle orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.connections.domain.event_enum.provider_enums import OAuthPollStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class OAuthDeviceAuthorization:
    """Device authorization values returned by an OAuth provider."""

    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str | None
    expires_at: datetime
    interval_seconds: int


@dataclass(frozen=True, slots=True, kw_only=True)
class OAuthTokenSet:
    """OAuth token values that must stay inside encrypted secret storage."""

    access_token: str
    refresh_token: str | None
    expires_at: datetime
    token_type: str
    scope: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class OAuthPollResult:
    """Result of polling an OAuth device authorization."""

    status: OAuthPollStatus
    token_set: OAuthTokenSet | None
    interval_seconds: int | None
    message: str | None
