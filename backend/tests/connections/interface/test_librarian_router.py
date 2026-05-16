"""Librarian provider router contract tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest
from app.connections.application.librarian_service import LibrarianService
from app.connections.domain.contracts.librarian_provider_contracts import (
    LibrarianProviderCreate,
    LibrarianProviderUpdate,
)
from app.connections.domain.entities.read_models import LibrarianProvider
from app.connections.domain.event_enum.provider_enums import ProviderSecretKey
from app.connections.domain.repositories.librarian_repository import (
    ILibrarianProviderRepository,
    IProviderSecretRepository,
)
from app.connections.infrastructure.librarians.clients import LibrarianClientFactory
from app.main import app
from app.shared.types.extra_types import JSONValue
from fastapi.testclient import TestClient
from tests.shared.provider_overrides import override_library_provider


class FakeLibrarianProviderRepository(ILibrarianProviderRepository):
    """In-memory provider repository for router contract tests."""

    def __init__(self) -> None:
        """Initialize empty provider storage."""
        self.created: LibrarianProvider | None = None

    async def create(self, payload: LibrarianProviderCreate) -> LibrarianProvider:
        """Create a provider entry."""
        provider = LibrarianProvider(
            id="00000000-0000-4000-8000-000000000501",
            name=payload.name,
            provider_type=payload.provider_type.value,
            auth_type=payload.auth_type.value,
            enabled=payload.enabled,
            config=payload.config,
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
        self, provider_id: str, payload: LibrarianProviderUpdate
    ) -> LibrarianProvider:
        """Patch provider settings."""
        if self.created is None or self.created.id != provider_id:
            raise ValueError(f"Provider not found: {provider_id}")
        values = payload.to_record()
        current = self.created
        config_value = values.get("config")
        provider = LibrarianProvider(
            id=current.id,
            name=str(values.get("name", current.name)),
            provider_type=str(values.get("provider_type", current.provider_type)),
            auth_type=str(values.get("auth_type", current.auth_type)),
            enabled=bool(values.get("enabled", current.enabled)),
            config=config_value if isinstance(config_value, dict) else current.config,
            created_at=current.created_at,
            updated_at=datetime(2026, 5, 12, 10, 5, tzinfo=UTC),
        )
        self.created = provider
        return provider

    async def delete(self, provider_id: str) -> None:
        """Delete one provider."""


class FakeProviderSecretRepository(IProviderSecretRepository):
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

    with (
        override_library_provider("librarian_service", override_librarian_service()),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post("/settings/connections", json=payload)

    return response.status_code, response.json()


def test_create_librarian_provider_accepts_json_enum_values_and_redacts_secret() -> (
    None
):
    """POST /settings/connections should accept public JSON and omit secrets."""

    provider_repo = FakeLibrarianProviderRepository()
    secret_repo = FakeProviderSecretRepository()

    def override_librarian_service() -> LibrarianService:
        return LibrarianService(provider_repo=provider_repo, secret_repo=secret_repo)

    with (
        override_library_provider("librarian_service", override_librarian_service()),
        TestClient(app) as client,
    ):
        response = client.post(
            "/settings/connections",
            json={
                "name": "default-openai",
                "provider_type": "OPENAI",
                "auth_type": "API_KEY",
                "enabled": True,
                "config": {"model": "gpt-5.5"},
                "api_key": "secret-key",
            },
        )

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
    """POST /settings/connections should return 422 for invalid enum strings."""
    payload = _valid_create_provider_payload()
    payload[field] = invalid_value

    status_code, body = _post_create_provider(payload)

    assert status_code == 422
    errors = cast(list[dict[str, object]], body["detail"])
    assert any(error["loc"] == ["body", field] for error in errors)


def test_create_librarian_provider_rejects_api_key_auth_without_api_key() -> None:
    """POST /settings/connections should reject API_KEY auth without api_key."""
    payload = _valid_create_provider_payload()
    payload.pop("api_key")

    status_code, body = _post_create_provider(payload)

    assert status_code == 400
    assert body == {"detail": "API_KEY auth requires api_key"}


def test_create_librarian_provider_rejects_oauth_auth_without_token() -> None:
    """POST /settings/connections should keep OPENAI API-key only."""
    payload = _valid_create_provider_payload()
    payload["auth_type"] = "OAUTH"
    payload.pop("api_key")

    status_code, body = _post_create_provider(payload)

    assert status_code == 400
    assert body == {"detail": "Provider type OPENAI does not support OAUTH auth"}


def test_create_openai_codex_oauth_provider_accepts_pending_device_flow_without_token() -> (
    None
):
    """POST /settings/connections should allow pending Codex OAuth connection."""
    payload = {
        "name": "codex-oauth",
        "provider_type": "OPENAI_CODEX",
        "auth_type": "OAUTH",
        "enabled": False,
        "config": {"base_url": "https://chatgpt.com/backend-api/codex"},
    }
    provider_repo = FakeLibrarianProviderRepository()
    secret_repo = FakeProviderSecretRepository()

    def override_librarian_service() -> LibrarianService:
        return LibrarianService(provider_repo=provider_repo, secret_repo=secret_repo)

    with (
        override_library_provider("librarian_service", override_librarian_service()),
        TestClient(app) as client,
    ):
        response = client.post("/settings/connections", json=payload)

    assert response.status_code == 201
    assert response.json() == {
        "id": "00000000-0000-4000-8000-000000000501",
        "name": "codex-oauth",
        "provider_type": "OPENAI_CODEX",
        "auth_type": "OAUTH",
        "enabled": False,
        "config": {"base_url": "https://chatgpt.com/backend-api/codex"},
        "created_at": "2026-05-12T10:00:00Z",
        "updated_at": "2026-05-12T10:00:00Z",
    }
    assert secret_repo.secrets == {}


def test_create_openai_codex_rejects_api_key_auth_without_secret_leak() -> None:
    """POST /settings/connections should reject Codex OAuth provider API keys."""
    payload = _valid_create_provider_payload()
    payload["provider_type"] = "OPENAI_CODEX"
    payload["api_key"] = "do-not-echo-api-key"

    status_code, body = _post_create_provider(payload)

    assert status_code == 400
    assert body == {
        "detail": "Provider type OPENAI_CODEX does not support API_KEY auth"
    }
    assert "do-not-echo-api-key" not in str(body)


def test_patch_librarian_provider_rejects_oauth_switch_without_token() -> None:
    """PATCH /settings/connections should not switch OPENAI to OAuth."""
    provider_repo = FakeLibrarianProviderRepository()
    secret_repo = FakeProviderSecretRepository()

    def override_librarian_service() -> LibrarianService:
        return LibrarianService(provider_repo=provider_repo, secret_repo=secret_repo)

    with (
        override_library_provider("librarian_service", override_librarian_service()),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        created = client.post(
            "/settings/connections",
            json=_valid_create_provider_payload(),
        )
        response = client.patch(
            f"/settings/connections/{created.json()['id']}",
            json={"auth_type": "OAUTH"},
        )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Provider type OPENAI does not support OAUTH auth"
    }


def test_patch_librarian_provider_stores_oauth_token_without_exposing_secret() -> None:
    """PATCH /settings/connections should persist Codex OAuth token but redact response."""
    provider_repo = FakeLibrarianProviderRepository()
    secret_repo = FakeProviderSecretRepository()

    def override_librarian_service() -> LibrarianService:
        return LibrarianService(provider_repo=provider_repo, secret_repo=secret_repo)

    with (
        override_library_provider("librarian_service", override_librarian_service()),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        created = client.post(
            "/settings/connections",
            json={
                "name": "codex-oauth",
                "provider_type": "OPENAI_CODEX",
                "auth_type": "OAUTH",
                "enabled": False,
                "config": {"base_url": "https://chatgpt.com/backend-api/codex"},
            },
        )
        provider_id = str(created.json()["id"])
        response = client.patch(
            f"/settings/connections/{provider_id}",
            json={
                "auth_type": "OAUTH",
                "oauth_access_token": "dummy-oauth-token",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "id": "00000000-0000-4000-8000-000000000501",
        "name": "codex-oauth",
        "provider_type": "OPENAI_CODEX",
        "auth_type": "OAUTH",
        "enabled": False,
        "config": {"base_url": "https://chatgpt.com/backend-api/codex"},
        "created_at": "2026-05-12T10:00:00Z",
        "updated_at": "2026-05-12T10:05:00Z",
    }
    assert "oauth_access_token" not in body
    assert "api_key" not in body
    assert (
        secret_repo.secrets[(provider_id, "oauth_access_token")] == "dummy-oauth-token"
    )


def test_patch_librarian_provider_switches_identity_and_purges_old_secret() -> None:
    """PATCH /settings/connections should clear stale secrets on auth identity change."""
    provider_repo = FakeLibrarianProviderRepository()
    secret_repo = FakeProviderSecretRepository()

    def override_librarian_service() -> LibrarianService:
        return LibrarianService(provider_repo=provider_repo, secret_repo=secret_repo)

    with (
        override_library_provider("librarian_service", override_librarian_service()),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        created = client.post(
            "/settings/connections",
            json=_valid_create_provider_payload(),
        )
        provider_id = str(created.json()["id"])
        response = client.patch(
            f"/settings/connections/{provider_id}",
            json={
                "provider_type": "OPENAI_CODEX",
                "auth_type": "OAUTH",
                "config": {"base_url": "https://chatgpt.com/backend-api/codex"},
            },
        )

    assert response.status_code == 200
    assert response.json()["provider_type"] == "OPENAI_CODEX"
    assert response.json()["auth_type"] == "OAUTH"
    assert secret_repo.secrets == {}


def test_create_openai_codex_oauth_rejects_unapproved_endpoint() -> None:
    """POST /settings/connections should reject OAuth endpoints outside allowlist."""
    payload: dict[str, JSONValue] = {
        "name": "codex-oauth",
        "provider_type": "OPENAI_CODEX",
        "auth_type": "OAUTH",
        "enabled": False,
        "config": {
            "device_authorization_url": "http://127.0.0.1/device",
            "token_url": "https://auth.openai.com/oauth/token",
            "client_id": "codex-client",
        },
    }

    status_code, body = _post_create_provider(payload)

    assert status_code == 400
    assert body == {
        "detail": (
            "OAuth config device_authorization_url must use an approved HTTPS endpoint"
        )
    }


def test_patch_openai_codex_oauth_rejects_endpoint_change_with_tokens() -> None:
    """PATCH /settings/connections should not retarget stored OAuth secrets."""
    provider_repo = FakeLibrarianProviderRepository()
    secret_repo = FakeProviderSecretRepository()

    def override_librarian_service() -> LibrarianService:
        return LibrarianService(provider_repo=provider_repo, secret_repo=secret_repo)

    original_config = {
        "device_authorization_url": (
            "https://auth.openai.com/api/accounts/deviceauth/usercode"
        ),
        "token_url": "https://auth.openai.com/oauth/token",
        "client_id": "codex-client",
    }
    with (
        override_library_provider("librarian_service", override_librarian_service()),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        created = client.post(
            "/settings/connections",
            json={
                "name": "codex-oauth",
                "provider_type": "OPENAI_CODEX",
                "auth_type": "OAUTH",
                "enabled": False,
                "config": original_config,
            },
        )
        provider_id = str(created.json()["id"])
        secret_repo.secrets[(provider_id, "oauth_refresh_token")] = "refresh-secret"
        response = client.patch(
            f"/settings/connections/{provider_id}",
            json={
                "config": {
                    **original_config,
                    "client_id": "rotated-client",
                }
            },
        )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "OAuth endpoint config cannot change while OAuth tokens are stored"
    }
    assert secret_repo.secrets[(provider_id, "oauth_refresh_token")] == "refresh-secret"
    assert "refresh-secret" not in response.text


def test_create_librarian_provider_rejects_credentials_in_config_without_leak() -> None:
    """POST /settings/connections should reject config credentials without echoing values."""
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
    """PATCH /settings/connections should reject config credentials without echoing values."""
    provider_repo = FakeLibrarianProviderRepository()
    secret_repo = FakeProviderSecretRepository()

    def override_librarian_service() -> LibrarianService:
        return LibrarianService(provider_repo=provider_repo, secret_repo=secret_repo)

    with (
        override_library_provider("librarian_service", override_librarian_service()),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        created = client.post(
            "/settings/connections",
            json=_valid_create_provider_payload(),
        )
        response = client.patch(
            f"/settings/connections/{created.json()['id']}",
            json={"config": {"password": "do-not-echo-patch-secret"}},
        )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Provider config must not include credential fields"
    }
    assert "do-not-echo-patch-secret" not in response.text


def test_test_librarian_provider_reports_disabled_before_secret_checks() -> None:
    """POST /settings/connections/{id}/test should not use credentials for disabled providers."""
    provider_repo = FakeLibrarianProviderRepository()
    secret_repo = FakeProviderSecretRepository()

    def override_librarian_service() -> LibrarianService:
        return LibrarianService(provider_repo=provider_repo, secret_repo=secret_repo)

    with (
        override_library_provider("librarian_service", override_librarian_service()),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        created = client.post(
            "/settings/connections",
            json={**_valid_create_provider_payload(), "enabled": False},
        )
        provider_id = str(created.json()["id"])
        response = client.post(
            f"/settings/connections/{provider_id}/test",
            json={"test_query": "ping"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "provider_id": "00000000-0000-4000-8000-000000000501",
        "ok": False,
        "message": "provider disabled",
    }


def test_test_librarian_provider_does_not_echo_sensitive_test_query() -> None:
    """POST /settings/connections/{id}/test should not echo caller query text."""
    provider_repo = FakeLibrarianProviderRepository()
    secret_repo = FakeProviderSecretRepository()

    def override_librarian_service() -> LibrarianService:
        return LibrarianService(
            provider_repo=provider_repo,
            secret_repo=secret_repo,
            client_factory=LibrarianClientFactory(),
        )

    with (
        override_library_provider("librarian_service", override_librarian_service()),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        created = client.post(
            "/settings/connections",
            json=_valid_create_provider_payload(),
        )
        provider_id = str(created.json()["id"])
        response = client.post(
            f"/settings/connections/{provider_id}/test",
            json={"test_query": "api_key=do-not-echo-query-secret"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "provider_id": "00000000-0000-4000-8000-000000000501",
        "ok": True,
        "message": "OPENAI SDK client dry-run accepted query",
    }
    assert "do-not-echo-query-secret" not in response.text


def test_test_librarian_provider_returns_not_found_without_internal_detail() -> None:
    """POST /settings/connections/{id}/test should map missing providers to 404."""
    provider_repo = FakeLibrarianProviderRepository()
    secret_repo = FakeProviderSecretRepository()

    def override_librarian_service() -> LibrarianService:
        return LibrarianService(provider_repo=provider_repo, secret_repo=secret_repo)

    with (
        override_library_provider("librarian_service", override_librarian_service()),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post(
            "/settings/connections/missing-provider/test",
            json={"test_query": "api_key=do-not-echo-missing-secret"},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Provider not found"}
    assert "missing-provider" not in response.text
    assert "do-not-echo-missing-secret" not in response.text


def test_delete_librarian_provider_removes_known_provider_secrets() -> None:
    """DELETE /settings/connections/{id} should clear provider secret material."""
    provider_repo = FakeLibrarianProviderRepository()
    secret_repo = FakeProviderSecretRepository()

    def override_librarian_service() -> LibrarianService:
        return LibrarianService(provider_repo=provider_repo, secret_repo=secret_repo)

    with (
        override_library_provider("librarian_service", override_librarian_service()),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        created = client.post(
            "/settings/connections",
            json=_valid_create_provider_payload(),
        )
        provider_id = str(created.json()["id"])
        for key in ProviderSecretKey:
            secret_repo.secrets[(provider_id, key.value)] = "secret-material"
        response = client.delete(f"/settings/connections/{provider_id}")

    assert response.status_code == 204
    assert secret_repo.secrets == {}
