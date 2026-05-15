"""Typed public payload contracts for librarian OAuth lifecycle responses."""

from __future__ import annotations

from datetime import datetime

from app.connections.domain.event_enum.provider_enums import (
    OAuthConnectionStatus,
    OAuthPollStatus,
)
from typing_extensions import TypedDict


class LibrarianOAuthStartPayload(TypedDict, closed=True):
    """Public payload returned after starting a device OAuth flow."""

    provider_id: str
    status: OAuthPollStatus
    user_code: str
    verification_uri: str
    verification_uri_complete: str | None
    expires_at: datetime
    interval_seconds: int


class LibrarianOAuthStatusPayload(TypedDict, closed=True):
    """Public OAuth state payload without credential material."""

    provider_id: str
    status: OAuthConnectionStatus
    connected: bool
    expires_at: datetime | None
    refresh_required: bool
    message: str | None
