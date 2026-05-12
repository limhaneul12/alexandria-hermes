"""Librarian provider schemas."""

from __future__ import annotations

from datetime import datetime

from app.library.domain.entities.enums import AuthType, ProviderType
from app.library.interface.schemas._types import StrictSchema
from app.shared.types.extra_types import JSONValue
from pydantic import ConfigDict, Field


class LibrarianProviderCreateRequest(StrictSchema):
    """Payload for creating a provider configuration."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "default-openai",
                    "provider_type": "OPENAI",
                    "auth_type": "API_KEY",
                    "enabled": True,
                    "config": {"model": "gpt-5.5"},
                    "api_key": "sk-local-redacted",
                    "oauth_access_token": None,
                }
            ]
        }
    )

    name: str
    provider_type: ProviderType
    auth_type: AuthType
    enabled: bool = True
    config: dict[str, JSONValue] = Field(default_factory=dict)
    api_key: str | None = None
    oauth_access_token: str | None = None


class LibrarianProviderPatchRequest(StrictSchema):
    """Payload for updating provider configuration."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "enabled": False,
                    "config": {"model": "gpt-5.5", "timeout_seconds": 30},
                }
            ]
        }
    )

    name: str | None = None
    provider_type: ProviderType | None = None
    auth_type: AuthType | None = None
    enabled: bool | None = None
    config: dict[str, JSONValue] | None = None
    api_key: str | None = None
    oauth_access_token: str | None = None


class LibrarianProviderResponse(StrictSchema):
    """Provider response model with timestamps."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "name": "default-openai",
                    "provider_type": "OPENAI",
                    "auth_type": "API_KEY",
                    "enabled": True,
                    "config": {"model": "gpt-5.5"},
                    "created_at": "2026-05-12T10:00:00Z",
                    "updated_at": "2026-05-12T10:05:00Z",
                }
            ]
        }
    )

    id: int
    name: str
    provider_type: ProviderType
    auth_type: AuthType
    enabled: bool
    config: dict[str, JSONValue]
    created_at: datetime
    updated_at: datetime


class LibrarianProviderTestRequest(StrictSchema):
    """Payload for connection test."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"test_query": "Suggest a FastAPI testing skill."}]
        }
    )

    test_query: str = "ping"


class LibrarianProviderTestResponse(StrictSchema):
    """Provider test response."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "provider_id": 1,
                    "ok": True,
                    "message": "Provider responded successfully.",
                }
            ]
        }
    )

    provider_id: int
    ok: bool
    message: str
