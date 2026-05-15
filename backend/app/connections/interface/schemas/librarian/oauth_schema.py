"""Pydantic I/O schemas for librarian OAuth lifecycle routes."""

from __future__ import annotations

from datetime import datetime

from app.connections.domain.event_enum.provider_enums import (
    OAuthConnectionStatus,
    OAuthPollStatus,
)
from app.library.interface.schemas._types import StrictSchema
from pydantic import ConfigDict


class LibrarianOAuthStartResponse(StrictSchema):
    """Response returned after starting a device OAuth flow."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "provider_id": "00000000-0000-4000-8000-000000000456",
                    "status": "pending",
                    "user_code": "ABCD-1234",
                    "verification_uri": "https://login.example/device",
                    "verification_uri_complete": (
                        "https://login.example/device?user_code=ABCD-1234"
                    ),
                    "expires_at": "2026-05-15T12:10:00Z",
                    "interval_seconds": 5,
                }
            ]
        }
    )

    provider_id: str
    status: OAuthPollStatus
    user_code: str
    verification_uri: str
    verification_uri_complete: str | None
    expires_at: datetime
    interval_seconds: int


class LibrarianOAuthStatusResponse(StrictSchema):
    """OAuth connection status response without credential material."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "provider_id": "00000000-0000-4000-8000-000000000456",
                    "status": "connected",
                    "connected": True,
                    "expires_at": "2026-05-15T13:00:00Z",
                    "refresh_required": False,
                    "message": None,
                }
            ]
        }
    )

    provider_id: str
    status: OAuthConnectionStatus
    connected: bool
    expires_at: datetime | None
    refresh_required: bool
    message: str | None
