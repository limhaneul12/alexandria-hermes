"""Librarian OAuth lifecycle router contract tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.connections.application.librarians.oauth_client import OAuthProviderClient
from app.connections.application.librarians.oauth_service import LibrarianOAuthService
from app.connections.domain.contracts.librarian_oauth_contracts import (
    OAuthDeviceAuthorization,
    OAuthPollResult,
    OAuthTokenSet,
)
from app.connections.domain.contracts.librarian_provider_contracts import (
    LibrarianProviderCreate,
    LibrarianProviderUpdate,
)
from app.connections.domain.entities.read_models import LibrarianProvider
from app.connections.domain.event_enum.provider_enums import (
    AuthType,
    OAuthPollStatus,
    ProviderSecretKey,
    ProviderType,
)
from app.connections.domain.repositories.librarian_repository import (
    ILibrarianProviderRepository,
    IProviderSecretRepository,
)
from app.main import app
from app.shared.types.extra_types import JSONObject
from fastapi.testclient import TestClient
from tests.shared.provider_overrides import override_library_provider

PROVIDER_ID = "00000000-0000-4000-8000-000000000777"
FIXED_NOW = datetime(2026, 5, 15, 12, 0, tzinfo=UTC)


class StaticProviderRepository(ILibrarianProviderRepository):
    """Provider repository test double for one stored provider."""

    def __init__(self, provider: LibrarianProvider) -> None:
        """Store the provider returned by lookups."""
        self.provider = provider
        self.deleted_provider_id: str | None = None

    async def create(self, payload: LibrarianProviderCreate) -> LibrarianProvider:
        """Create is unused by OAuth route tests."""
        raise NotImplementedError

    async def get(self, provider_id: str) -> LibrarianProvider | None:
        """Return the stored provider when ids match."""
        if provider_id != self.provider.id:
            return None
        return self.provider

    async def list_all(self) -> list[LibrarianProvider]:
        """Return the stored provider."""
        return [self.provider]

    async def update(
        self, provider_id: str, payload: LibrarianProviderUpdate
    ) -> LibrarianProvider:
        """Update is unused by OAuth route tests."""
        raise NotImplementedError

    async def delete(self, provider_id: str) -> None:
        """Record the deleted provider id."""
        self.deleted_provider_id = provider_id


class MemorySecretRepository(IProviderSecretRepository):
    """In-memory secret repository for OAuth route tests."""

    def __init__(self) -> None:
        """Initialize empty secret storage."""
        self.secrets: dict[tuple[str, str], str] = {}
        self.deleted: list[tuple[str, str]] = []

    async def resolve(self, provider_id: str, key_name: str) -> str | None:
        """Resolve a stored secret."""
        return self.secrets.get((provider_id, key_name))

    async def set_secret(self, *, provider_id: str, key_name: str, value: str) -> None:
        """Store a secret value."""
        self.secrets[(provider_id, key_name)] = value

    async def delete_for_provider(self, provider_id: str, key_name: str) -> None:
        """Delete a provider secret value."""
        self.deleted.append((provider_id, key_name))
        self.secrets.pop((provider_id, key_name), None)


class RecordingOAuthClient(OAuthProviderClient):
    """OAuth client fake returning deterministic device and token payloads."""

    def __init__(self) -> None:
        """Initialize recorded boundary calls."""
        self.start_calls: list[str] = []
        self.poll_calls: list[str] = []
        self.refresh_calls: list[str] = []

    async def start_device_authorization(
        self, provider: LibrarianProvider
    ) -> OAuthDeviceAuthorization:
        """Return a deterministic device authorization response."""
        self.start_calls.append(provider.id)
        return OAuthDeviceAuthorization(
            device_code="device-secret-value",
            user_code="ABCD-1234",
            verification_uri="https://login.example/device",
            verification_uri_complete="https://login.example/device?user_code=ABCD-1234",
            expires_at=FIXED_NOW + timedelta(minutes=10),
            interval_seconds=5,
        )

    async def poll_device_token(
        self,
        provider: LibrarianProvider,
        device_code: str,
    ) -> OAuthPollResult:
        """Return a successful token result for the provided device code."""
        self.poll_calls.append(device_code)
        return OAuthPollResult(
            status=OAuthPollStatus.CONNECTED,
            token_set=OAuthTokenSet(
                access_token="access-token-secret",
                refresh_token="refresh-token-secret",
                expires_at=FIXED_NOW + timedelta(hours=1),
                token_type="Bearer",
                scope="openid profile",
            ),
            interval_seconds=None,
            message=None,
        )

    async def refresh_token(
        self,
        provider: LibrarianProvider,
        refresh_token: str,
    ) -> OAuthTokenSet:
        """Return a deterministic rotated token set."""
        self.refresh_calls.append(refresh_token)
        return OAuthTokenSet(
            access_token="rotated-access-token",
            refresh_token="rotated-refresh-token",
            expires_at=FIXED_NOW + timedelta(hours=2),
            token_type="Bearer",
            scope="openid profile email",
        )


def _provider(
    *,
    provider_type: ProviderType = ProviderType.OPENAI_CODEX,
    auth_type: AuthType = AuthType.OAUTH,
    config: JSONObject | None = None,
) -> LibrarianProvider:
    """Build a provider read model for OAuth lifecycle tests."""
    return LibrarianProvider(
        id=PROVIDER_ID,
        name="codex-oauth",
        provider_type=provider_type.value,
        auth_type=auth_type.value,
        enabled=False,
        config={} if config is None else config,
        created_at=FIXED_NOW,
        updated_at=FIXED_NOW,
    )


def _oauth_service(
    *,
    provider: LibrarianProvider | None = None,
    secrets: MemorySecretRepository | None = None,
    oauth_client: RecordingOAuthClient | None = None,
) -> tuple[LibrarianOAuthService, MemorySecretRepository, RecordingOAuthClient]:
    """Create an OAuth service with in-memory boundaries."""
    secret_repo = MemorySecretRepository() if secrets is None else secrets
    client = RecordingOAuthClient() if oauth_client is None else oauth_client
    service = LibrarianOAuthService(
        provider_repo=StaticProviderRepository(
            _provider() if provider is None else provider
        ),
        secret_repo=secret_repo,
        oauth_client=client,
        now_provider=lambda: FIXED_NOW,
    )
    return service, secret_repo, client


def test_start_oauth_returns_user_instructions_and_stores_device_code_without_leak() -> (
    None
):
    """POST oauth/start should expose user instructions but never device_code."""
    service, secret_repo, oauth_client = _oauth_service()

    with (
        override_library_provider("librarian_oauth_service", service),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post(f"/settings/connections/{PROVIDER_ID}/oauth/start")

    body = response.json()
    assert response.status_code == 200
    assert body == {
        "provider_id": PROVIDER_ID,
        "status": "pending",
        "user_code": "ABCD-1234",
        "verification_uri": "https://login.example/device",
        "verification_uri_complete": "https://login.example/device?user_code=ABCD-1234",
        "expires_at": "2026-05-15T12:10:00Z",
        "interval_seconds": 5,
    }
    assert oauth_client.start_calls == [PROVIDER_ID]
    assert (
        secret_repo.secrets[(PROVIDER_ID, ProviderSecretKey.OAUTH_DEVICE_CODE.value)]
        == "device-secret-value"
    )
    assert "device-secret-value" not in response.text
    assert "oauth_device_code" not in response.text
    assert "access-token-secret" not in response.text
    assert "refresh-token-secret" not in response.text


def test_start_oauth_accepts_provider_name_alias() -> None:
    """POST oauth/start should resolve a provider by user-facing name."""
    service, secret_repo, oauth_client = _oauth_service()

    with (
        override_library_provider("librarian_oauth_service", service),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post("/settings/connections/codex-oauth/oauth/start")

    body = response.json()
    assert response.status_code == 200
    assert body["provider_id"] == PROVIDER_ID
    assert oauth_client.start_calls == [PROVIDER_ID]
    assert (
        secret_repo.secrets[(PROVIDER_ID, ProviderSecretKey.OAUTH_DEVICE_CODE.value)]
        == "device-secret-value"
    )
    assert "device-secret-value" not in response.text


def test_poll_oauth_success_stores_tokens_and_redacts_response() -> None:
    """POST oauth/poll should persist token material while returning only status."""
    service, secret_repo, oauth_client = _oauth_service()
    secret_repo.secrets[(PROVIDER_ID, ProviderSecretKey.OAUTH_DEVICE_CODE.value)] = (
        "device-secret-value"
    )
    secret_repo.secrets[
        (PROVIDER_ID, ProviderSecretKey.OAUTH_DEVICE_EXPIRES_AT.value)
    ] = (FIXED_NOW + timedelta(minutes=10)).isoformat()

    with (
        override_library_provider("librarian_oauth_service", service),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post(f"/settings/connections/{PROVIDER_ID}/oauth/poll")

    body = response.json()
    assert response.status_code == 200
    assert body == {
        "provider_id": PROVIDER_ID,
        "status": "connected",
        "connected": True,
        "expires_at": "2026-05-15T13:00:00Z",
        "refresh_required": False,
        "message": None,
    }
    assert oauth_client.poll_calls == ["device-secret-value"]
    assert (
        secret_repo.secrets[(PROVIDER_ID, ProviderSecretKey.OAUTH_ACCESS_TOKEN.value)]
        == "access-token-secret"
    )
    assert (
        secret_repo.secrets[(PROVIDER_ID, ProviderSecretKey.OAUTH_REFRESH_TOKEN.value)]
        == "refresh-token-secret"
    )
    assert (
        secret_repo.secrets[(PROVIDER_ID, ProviderSecretKey.OAUTH_EXPIRES_AT.value)]
        == "2026-05-15T13:00:00+00:00"
    )
    assert (
        PROVIDER_ID,
        ProviderSecretKey.OAUTH_DEVICE_CODE.value,
    ) not in secret_repo.secrets
    assert "access-token-secret" not in response.text
    assert "refresh-token-secret" not in response.text
    assert "device-secret-value" not in response.text


@pytest.mark.parametrize(
    ("expires_delta", "expected_refresh_calls", "expected_access_token"),
    [
        (timedelta(minutes=5), [], "current-access-token"),
        (timedelta(seconds=60), ["current-refresh-token"], "rotated-access-token"),
    ],
)
def test_refresh_oauth_uses_refresh_skew_without_leaking_tokens(
    expires_delta: timedelta,
    expected_refresh_calls: list[str],
    expected_access_token: str,
) -> None:
    """POST oauth/refresh should rotate only when expiry falls within the skew."""
    service, secret_repo, oauth_client = _oauth_service()
    secret_repo.secrets[(PROVIDER_ID, ProviderSecretKey.OAUTH_ACCESS_TOKEN.value)] = (
        "current-access-token"
    )
    secret_repo.secrets[(PROVIDER_ID, ProviderSecretKey.OAUTH_REFRESH_TOKEN.value)] = (
        "current-refresh-token"
    )
    secret_repo.secrets[(PROVIDER_ID, ProviderSecretKey.OAUTH_EXPIRES_AT.value)] = (
        FIXED_NOW + expires_delta
    ).isoformat()

    with (
        override_library_provider("librarian_oauth_service", service),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post(f"/settings/connections/{PROVIDER_ID}/oauth/refresh")

    assert response.status_code == 200
    assert response.json() == {
        "provider_id": PROVIDER_ID,
        "status": "connected",
        "connected": True,
        "expires_at": (
            "2026-05-15T12:05:00Z"
            if not expected_refresh_calls
            else "2026-05-15T14:00:00Z"
        ),
        "refresh_required": False,
        "message": None,
    }
    assert oauth_client.refresh_calls == expected_refresh_calls
    assert (
        secret_repo.secrets[(PROVIDER_ID, ProviderSecretKey.OAUTH_ACCESS_TOKEN.value)]
        == expected_access_token
    )
    assert "current-refresh-token" not in response.text
    assert "rotated-access-token" not in response.text


def test_status_oauth_reports_pending_without_leaking_device_code() -> None:
    """GET oauth/status should report pending device flow without device_code."""
    service, secret_repo, oauth_client = _oauth_service()
    secret_repo.secrets[(PROVIDER_ID, ProviderSecretKey.OAUTH_DEVICE_CODE.value)] = (
        "device-secret-value"
    )
    secret_repo.secrets[
        (PROVIDER_ID, ProviderSecretKey.OAUTH_DEVICE_EXPIRES_AT.value)
    ] = (FIXED_NOW + timedelta(minutes=10)).isoformat()

    with (
        override_library_provider("librarian_oauth_service", service),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.get(f"/settings/connections/{PROVIDER_ID}/oauth/status")

    assert response.status_code == 200
    assert response.json() == {
        "provider_id": PROVIDER_ID,
        "status": "pending",
        "connected": False,
        "expires_at": None,
        "refresh_required": False,
        "message": None,
    }
    assert oauth_client.start_calls == []
    assert "device-secret-value" not in response.text


def test_start_oauth_rejects_non_codex_provider() -> None:
    """POST oauth/start should reject providers outside OPENAI_CODEX OAuth."""
    service, _secret_repo, _oauth_client = _oauth_service(
        provider=_provider(
            provider_type=ProviderType.OPENAI, auth_type=AuthType.API_KEY
        )
    )

    with (
        override_library_provider("librarian_oauth_service", service),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post(f"/settings/connections/{PROVIDER_ID}/oauth/start")

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Provider type OPENAI does not support OAuth lifecycle"
    }
