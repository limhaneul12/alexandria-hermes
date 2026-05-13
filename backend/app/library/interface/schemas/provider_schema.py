"""Librarian provider schemas."""

from __future__ import annotations

from datetime import datetime

from app.library.domain.entities.enums import AuthType, ProviderType
from app.library.interface.schemas._types import StrictSchema
from app.shared.types.extra_types import JSONValue
from pydantic import ConfigDict, Field, field_validator


def _provider_type(value: object) -> ProviderType:
    """Accept public JSON provider type values at API boundaries."""
    if isinstance(value, ProviderType):
        return value
    if isinstance(value, str):
        return ProviderType(value)
    raise ValueError("provider_type must be a valid provider type")


def _auth_type(value: object) -> AuthType:
    """Accept public JSON auth type values at API boundaries."""
    if isinstance(value, AuthType):
        return value
    if isinstance(value, str):
        return AuthType(value)
    raise ValueError("auth_type must be a valid auth type")


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

    @field_validator("provider_type", mode="before")
    @classmethod
    def parse_provider_type(cls, value: object) -> ProviderType:
        """Parse JSON provider type values."""
        return _provider_type(value)

    @field_validator("auth_type", mode="before")
    @classmethod
    def parse_auth_type(cls, value: object) -> AuthType:
        """Parse JSON auth type values."""
        return _auth_type(value)


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

    @field_validator("provider_type", mode="before")
    @classmethod
    def parse_provider_type(cls, value: object) -> ProviderType | None:
        """Parse JSON provider type values when provided."""
        if value is None:
            return None
        return _provider_type(value)

    @field_validator("auth_type", mode="before")
    @classmethod
    def parse_auth_type(cls, value: object) -> AuthType | None:
        """Parse JSON auth type values when provided."""
        if value is None:
            return None
        return _auth_type(value)


class LibrarianProviderResponse(StrictSchema):
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
    config: dict[str, JSONValue]
    created_at: datetime
    updated_at: datetime

    @field_validator("provider_type", mode="before")
    @classmethod
    def parse_provider_type(cls, value: object) -> ProviderType:
        """Parse response provider type values from repository payloads."""
        return _provider_type(value)

    @field_validator("auth_type", mode="before")
    @classmethod
    def parse_auth_type(cls, value: object) -> AuthType:
        """Parse response auth type values from repository payloads."""
        return _auth_type(value)


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
