"""Librarian provider router contract tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.library.application.librarian_service import LibrarianService
from app.library.domain.entities.read_models import LibrarianProvider
from app.library.domain.repositories.librarian_repository import (
    LibrarianProviderRepository,
    ProviderSecretRepository,
)
from app.library.infrastructure.librarians.clients import LibrarianClientFactory
from app.library.interface.routers.dependencies import get_librarian_service
from app.main import app
from app.shared.types.extra_types import JSONValue
from fastapi.testclient import TestClient


class FakeLibrarianProviderRepository(LibrarianProviderRepository):
    """In-memory provider repository for router contract tests."""

    def __init__(self) -> None:
        """Initialize empty provider storage."""
        self.created: LibrarianProvider | None = None

    async def create(self, payload: dict[str, JSONValue]) -> LibrarianProvider:
        """Create a provider entry."""
        provider = LibrarianProvider(
            id="00000000-0000-4000-8000-000000000501",
            name=str(payload["name"]),
            provider_type=str(payload["provider_type"]),
            auth_type=str(payload["auth_type"]),
            enabled=bool(payload["enabled"]),
            config=payload["config"] if isinstance(payload["config"], dict) else {},
            created_at=datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
            updated_at=datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
        )
        self.created = provider
        return provider

    async def get(self, provider_id: str) -> LibrarianProvider | None:
        """Get one provider."""
        if self.created is None or self.created.id != provider_id:
            return None
        return self.created

    async def list_all(self) -> list[LibrarianProvider]:
        """List all providers."""
        return [] if self.created is None else [self.created]

    async def update(
        self, provider_id: str, payload: dict[str, JSONValue]
    ) -> LibrarianProvider:
        """Patch provider settings."""
        if self.created is None or self.created.id != provider_id:
            raise ValueError(f"Provider not found: {provider_id}")
        current = self.created
        provider = LibrarianProvider(
            id=current.id,
            name=str(payload.get("name", current.name)),
            provider_type=str(payload.get("provider_type", current.provider_type)),
            auth_type=str(payload.get("auth_type", current.auth_type)),
            enabled=bool(payload.get("enabled", current.enabled)),
            config=payload["config"]
            if isinstance(payload.get("config"), dict)
            else current.config,
            created_at=current.created_at,
            updated_at=datetime(2026, 5, 12, 10, 5, tzinfo=UTC),
        )
        self.created = provider
        return provider

    async def delete(self, provider_id: str) -> None:
        """Delete one provider."""


class FakeProviderSecretRepository(ProviderSecretRepository):
    """In-memory provider secret repository for router contract tests."""

    def __init__(self) -> None:
        """Initialize empty secret storage."""
        self.secrets: dict[tuple[str, str], str] = {}

    async def resolve(self, provider_id: str, key_name: str) -> str | None:
        """Return secret value by key name."""
        return self.secrets.get((provider_id, key_name))

    async def set_secret(self, *, provider_id: str, key_name: str, value: str) -> None:
        """Persist or update one provider secret."""
        self.secrets[(provider_id, key_name)] = value

    async def delete_for_provider(self, provider_id: str, key_name: str) -> None:
        """Delete one provider secret key."""
        self.secrets.pop((provider_id, key_name), None)


def _valid_create_provider_payload() -> dict[str, JSONValue]:
    """Return a valid provider creation payload for negative contract tests."""
    return {
        "name": "default-openai",
        "provider_type": "OPENAI",
        "auth_type": "API_KEY",
        "enabled": True,
        "config": {"model": "gpt-5.5"},
        "api_key": "secret-key",
    }


def _post_create_provider(
    payload: dict[str, JSONValue],
) -> tuple[int, dict[str, object]]:
    """Post a provider creation request with in-memory boundary fakes."""
    provider_repo = FakeLibrarianProviderRepository()
    secret_repo = FakeProviderSecretRepository()

    def override_librarian_service() -> LibrarianService:
        return LibrarianService(provider_repo=provider_repo, secret_repo=secret_repo)

    app.dependency_overrides[get_librarian_service] = override_librarian_service
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/settings/librarians", json=payload)
    finally:
        app.dependency_overrides.pop(get_librarian_service, None)

    return response.status_code, response.json()


def test_create_librarian_provider_accepts_json_enum_values_and_redacts_secret() -> (
    None
):
    """POST /settings/librarians should accept public JSON and omit secrets."""

    provider_repo = FakeLibrarianProviderRepository()
    secret_repo = FakeProviderSecretRepository()

    def override_librarian_service() -> LibrarianService:
        return LibrarianService(provider_repo=provider_repo, secret_repo=secret_repo)

    app.dependency_overrides[get_librarian_service] = override_librarian_service
    try:
        with TestClient(app) as client:
            response = client.post(
                "/settings/librarians",
                json={
                    "name": "default-openai",
                    "provider_type": "OPENAI",
                    "auth_type": "API_KEY",
                    "enabled": True,
                    "config": {"model": "gpt-5.5"},
                    "api_key": "secret-key",
                },
            )
    finally:
        app.dependency_overrides.pop(get_librarian_service, None)

    assert response.status_code == 201
    assert response.json() == {
        "id": "00000000-0000-4000-8000-000000000501",
        "name": "default-openai",
        "provider_type": "OPENAI",
        "auth_type": "API_KEY",
        "enabled": True,
        "config": {"model": "gpt-5.5"},
        "created_at": "2026-05-12T10:00:00Z",
        "updated_at": "2026-05-12T10:00:00Z",
    }
    assert secret_repo.secrets == {
        ("00000000-0000-4000-8000-000000000501", "api_key"): "secret-key"
    }


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("provider_type", "GEMINI"),
        ("auth_type", "TOKEN"),
    ],
)
def test_create_librarian_provider_rejects_invalid_enum_strings(
    field: str,
    invalid_value: str,
) -> None:
    """POST /settings/librarians should return 422 for invalid enum strings."""
    payload = _valid_create_provider_payload()
    payload[field] = invalid_value

    status_code, body = _post_create_provider(payload)

    assert status_code == 422
    assert any(error["loc"] == ["body", field] for error in body["detail"])


def test_create_librarian_provider_rejects_api_key_auth_without_api_key() -> None:
    """POST /settings/librarians should reject API_KEY auth without api_key."""
    payload = _valid_create_provider_payload()
    payload.pop("api_key")

    status_code, body = _post_create_provider(payload)

    assert status_code == 400
    assert body == {"detail": "API_KEY auth requires api_key"}


def test_create_librarian_provider_rejects_oauth_auth_without_token() -> None:
    """POST /settings/librarians should reject OAUTH auth without OAuth token."""
    payload = _valid_create_provider_payload()
    payload["auth_type"] = "OAUTH"
    payload.pop("api_key")

    status_code, body = _post_create_provider(payload)

    assert status_code == 400
    assert body == {"detail": "OAUTH auth requires oauth_access_token"}


def test_patch_librarian_provider_rejects_oauth_switch_without_token() -> None:
    """PATCH /settings/librarians should not switch to OAUTH without credentials."""
    provider_repo = FakeLibrarianProviderRepository()
    secret_repo = FakeProviderSecretRepository()

    def override_librarian_service() -> LibrarianService:
        return LibrarianService(provider_repo=provider_repo, secret_repo=secret_repo)

    app.dependency_overrides[get_librarian_service] = override_librarian_service
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            created = client.post(
                "/settings/librarians",
                json=_valid_create_provider_payload(),
            )
            response = client.patch(
                f"/settings/librarians/{created.json()['id']}",
                json={"auth_type": "OAUTH"},
            )
    finally:
        app.dependency_overrides.pop(get_librarian_service, None)

    assert response.status_code == 400
    assert response.json() == {"detail": "OAUTH auth requires oauth_access_token"}


def test_patch_librarian_provider_stores_oauth_token_without_exposing_secret() -> None:
    """PATCH /settings/librarians should persist OAuth token but redact response."""
    provider_repo = FakeLibrarianProviderRepository()
    secret_repo = FakeProviderSecretRepository()

    def override_librarian_service() -> LibrarianService:
        return LibrarianService(provider_repo=provider_repo, secret_repo=secret_repo)

    app.dependency_overrides[get_librarian_service] = override_librarian_service
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            created = client.post(
                "/settings/librarians",
                json=_valid_create_provider_payload(),
            )
            provider_id = str(created.json()["id"])
            response = client.patch(
                f"/settings/librarians/{provider_id}",
                json={
                    "auth_type": "OAUTH",
                    "oauth_access_token": "dummy-oauth-token",
                },
            )
    finally:
        app.dependency_overrides.pop(get_librarian_service, None)

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "id": "00000000-0000-4000-8000-000000000501",
        "name": "default-openai",
        "provider_type": "OPENAI",
        "auth_type": "OAUTH",
        "enabled": True,
        "config": {"model": "gpt-5.5"},
        "created_at": "2026-05-12T10:00:00Z",
        "updated_at": "2026-05-12T10:05:00Z",
    }
    assert "oauth_access_token" not in body
    assert "api_key" not in body
    assert secret_repo.secrets[(provider_id, "oauth_access_token")] == "dummy-oauth-token"


def test_create_librarian_provider_rejects_credentials_in_config_without_leak() -> None:
    """POST /settings/librarians should reject config credentials without echoing values."""
    payload = _valid_create_provider_payload()
    payload["config"] = {
        "model": "gpt-5.5",
        "nested": {"api_key": "do-not-echo-config-secret"},
    }

    status_code, body = _post_create_provider(payload)

    assert status_code == 400
    assert body == {"detail": "Provider config must not include credential fields"}
    assert "do-not-echo-config-secret" not in str(body)


def test_patch_librarian_provider_rejects_credentials_in_config_without_leak() -> None:
    """PATCH /settings/librarians should reject config credentials without echoing values."""
    provider_repo = FakeLibrarianProviderRepository()
    secret_repo = FakeProviderSecretRepository()

    def override_librarian_service() -> LibrarianService:
        return LibrarianService(provider_repo=provider_repo, secret_repo=secret_repo)

    app.dependency_overrides[get_librarian_service] = override_librarian_service
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            created = client.post(
                "/settings/librarians",
                json=_valid_create_provider_payload(),
            )
            response = client.patch(
                f"/settings/librarians/{created.json()['id']}",
                json={"config": {"password": "do-not-echo-patch-secret"}},
            )
    finally:
        app.dependency_overrides.pop(get_librarian_service, None)

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Provider config must not include credential fields"
    }
    assert "do-not-echo-patch-secret" not in response.text


def test_test_librarian_provider_reports_disabled_before_secret_checks() -> None:
    """POST /settings/librarians/{id}/test should not use credentials for disabled providers."""
    provider_repo = FakeLibrarianProviderRepository()
    secret_repo = FakeProviderSecretRepository()

    def override_librarian_service() -> LibrarianService:
        return LibrarianService(provider_repo=provider_repo, secret_repo=secret_repo)

    app.dependency_overrides[get_librarian_service] = override_librarian_service
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            created = client.post(
                "/settings/librarians",
                json={**_valid_create_provider_payload(), "enabled": False},
            )
            provider_id = str(created.json()["id"])
            response = client.post(
                f"/settings/librarians/{provider_id}/test",
                json={"test_query": "ping"},
            )
    finally:
        app.dependency_overrides.pop(get_librarian_service, None)

    assert response.status_code == 200
    assert response.json() == {
        "provider_id": "00000000-0000-4000-8000-000000000501",
        "ok": False,
        "message": "provider disabled",
    }


def test_test_librarian_provider_does_not_echo_sensitive_test_query() -> None:
    """POST /settings/librarians/{id}/test should not echo caller query text."""
    provider_repo = FakeLibrarianProviderRepository()
    secret_repo = FakeProviderSecretRepository()
    client_factory = LibrarianClientFactory(openai_constructor=lambda **kwargs: object())

    def override_librarian_service() -> LibrarianService:
        return LibrarianService(
            provider_repo=provider_repo,
            secret_repo=secret_repo,
            client_factory=client_factory,
        )

    app.dependency_overrides[get_librarian_service] = override_librarian_service
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            created = client.post(
                "/settings/librarians",
                json=_valid_create_provider_payload(),
            )
            provider_id = str(created.json()["id"])
            response = client.post(
                f"/settings/librarians/{provider_id}/test",
                json={"test_query": "api_key=do-not-echo-query-secret"},
            )
    finally:
        app.dependency_overrides.pop(get_librarian_service, None)

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "provider_id": "00000000-0000-4000-8000-000000000501",
        "ok": True,
        "message": "OPENAI SDK client dry-run accepted query",
    }
    assert "do-not-echo-query-secret" not in response.text


def test_test_librarian_provider_returns_not_found_without_internal_detail() -> None:
    """POST /settings/librarians/{id}/test should map missing providers to 404."""
    provider_repo = FakeLibrarianProviderRepository()
    secret_repo = FakeProviderSecretRepository()

    def override_librarian_service() -> LibrarianService:
        return LibrarianService(provider_repo=provider_repo, secret_repo=secret_repo)

    app.dependency_overrides[get_librarian_service] = override_librarian_service
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/settings/librarians/missing-provider/test",
                json={"test_query": "api_key=do-not-echo-missing-secret"},
            )
    finally:
        app.dependency_overrides.pop(get_librarian_service, None)

    assert response.status_code == 404
    assert response.json() == {"detail": "Provider not found"}
    assert "missing-provider" not in response.text
    assert "do-not-echo-missing-secret" not in response.text
