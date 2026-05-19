"""Librarian provider schemas."""

from __future__ import annotations

from datetime import datetime

from app.connections.domain.event_enum.provider_enums import AuthType, ProviderType
from app.connections.domain.types.librarian_provider_payload_types import (
    LibrarianProviderPatchPayload,
)
from app.shared.schemas.common_schemas import StrictRootSchemaModel, StrictSchemaModel
from app.shared.types.extra_types import JSONObject
from pydantic import ConfigDict, Field


class LibrarianProviderCreateRequest(StrictSchemaModel):
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
    config: JSONObject = Field(default_factory=dict)
    api_key: str | None = Field(
        default=None,
        repr=False,
        json_schema_extra={"writeOnly": True},
    )
    oauth_access_token: str | None = Field(
        default=None,
        repr=False,
        json_schema_extra={"writeOnly": True},
    )


class LibrarianProviderPatchRequest(StrictSchemaModel):
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
    config: JSONObject | None = None
    api_key: str | None = Field(
        default=None,
        repr=False,
        json_schema_extra={"writeOnly": True},
    )
    oauth_access_token: str | None = Field(
        default=None,
        repr=False,
        json_schema_extra={"writeOnly": True},
    )

    def to_payload(self) -> LibrarianProviderPatchPayload:
        """Return a typed service-layer patch payload.

        Returns:
            LibrarianProviderPatchPayload: Provider patch fields excluding absent values.
        """
        payload: LibrarianProviderPatchPayload = {}
        if self.name is not None:
            payload["name"] = self.name
        if self.provider_type is not None:
            payload["provider_type"] = self.provider_type
        if self.auth_type is not None:
            payload["auth_type"] = self.auth_type
        if self.enabled is not None:
            payload["enabled"] = self.enabled
        if self.config is not None:
            payload["config"] = self.config
        if self.api_key is not None:
            payload["api_key"] = self.api_key
        if self.oauth_access_token is not None:
            payload["oauth_access_token"] = self.oauth_access_token
        return payload


class LibrarianProviderResponse(StrictSchemaModel):
    """Provider response model with timestamps."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "00000000-0000-4000-8000-000000000456",
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

    id: str
    name: str
    provider_type: ProviderType
    auth_type: AuthType
    enabled: bool
    config: JSONObject
    created_at: datetime
    updated_at: datetime


class LibrarianProviderResponseList(
    StrictRootSchemaModel[list[LibrarianProviderResponse]]
):
    """Root response schema for librarian provider response arrays."""


class LibrarianProviderTestRequest(StrictSchemaModel):
    """Payload for connection test."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"test_query": "Suggest a FastAPI testing skill."}]
        }
    )

    test_query: str = "ping"


class LibrarianProviderTestResponse(StrictSchemaModel):
    """Provider test response."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "provider_id": "00000000-0000-4000-8000-000000000456",
                    "ok": True,
                    "message": "Provider responded successfully.",
                }
            ]
        }
    )

    provider_id: str
    ok: bool
    message: str
