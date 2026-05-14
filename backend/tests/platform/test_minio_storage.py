"""Behavior tests for platform MINIO storage integration."""

from __future__ import annotations

import socket
from datetime import UTC, datetime
from typing import cast

import pytest
from app.library.domain.contracts.librarian_provider_contracts import (
    LibrarianProviderCreate,
    LibrarianProviderUpdate,
)
from app.library.domain.entities.read_models import LibrarianProvider
from app.library.domain.repositories.librarian_repository import (
    ILibrarianProviderRepository,
    IProviderSecretRepository,
)
from app.platform.storage.minio_endpoint_safety import validate_minio_endpoint
from app.platform.storage.minio_object_content import (
    MinioClientBuilder,
    MinioObjectContentClient,
)
from app.platform.storage.minio_object_listing import MinioObjectListingClient
from app.platform.storage.minio_pinned_transport import PinnedPoolManager
from app.platform.storage.minio_types import MinioEndpoint
from minio.datatypes import Object as SdkMinioObject
from urllib3.exceptions import NewConnectionError


class FakeProviderRepository(ILibrarianProviderRepository):
    """In-memory provider repository for MINIO archive tests."""

    def __init__(self, providers: list[LibrarianProvider]) -> None:
        """Store providers returned by list_all."""
        self.providers = providers

    async def get(self, provider_id: str) -> LibrarianProvider | None:
        """Return one provider by ID."""
        provider = next(
            (provider for provider in self.providers if provider.id == provider_id),
            None,
        )
        return provider

    async def list_all(self) -> list[LibrarianProvider]:
        """Return configured providers."""
        return self.providers

    async def create(self, payload: LibrarianProviderCreate) -> LibrarianProvider:
        """Create is outside this test boundary."""
        raise NotImplementedError

    async def update(
        self, provider_id: str, payload: LibrarianProviderUpdate
    ) -> LibrarianProvider:
        """Update is outside this test boundary."""
        raise NotImplementedError

    async def delete(self, provider_id: str) -> None:
        """Delete is outside this test boundary."""
        raise NotImplementedError


class FakeSecretRepository(IProviderSecretRepository):
    """In-memory provider secret repository for MINIO archive tests."""

    def __init__(self, secret: str | None) -> None:
        """Store one secret value."""
        self.secret = secret

    async def resolve(self, provider_id: str, key_name: str) -> str | None:
        """Return the configured secret."""
        return self.secret

    async def set_secret(self, *, provider_id: str, key_name: str, value: str) -> None:
        """Secret mutation is outside this test boundary."""
        raise NotImplementedError

    async def delete_for_provider(self, provider_id: str, key_name: str) -> None:
        """Secret deletion is outside this test boundary."""
        raise NotImplementedError


class FakeMinioClient:
    """Boundary fake for the official MinIO SDK client."""

    def __init__(self, objects: list[SdkMinioObject]) -> None:
        """Store objects returned by list_objects."""
        self.objects = objects
        self.calls: list[dict[str, object]] = []

    def list_objects(
        self,
        bucket_name: str,
        prefix: str | None = None,
        recursive: bool = False,
    ) -> list[SdkMinioObject]:
        """Return configured objects and capture observable request shape."""
        self.calls.append(
            {
                "bucket_name": bucket_name,
                "prefix": prefix,
                "recursive": recursive,
            }
        )
        return self.objects


class FakeMinioObjectResponse:
    """Boundary fake for one SDK object body response."""

    def __init__(self, data: bytes) -> None:
        """Store response bytes."""
        self.data = data
        self.closed = False
        self.released = False
        self.read_sizes: list[int] = []

    def read(self, size: int) -> bytes:
        """Return bounded bytes like urllib3 response bodies."""
        self.read_sizes.append(size)
        return self.data[:size]

    def close(self) -> None:
        """Record close side effect."""
        self.closed = True

    def release_conn(self) -> None:
        """Record connection release side effect."""
        self.released = True


class FakeMinioContentClient:
    """Boundary fake for SDK object content reads."""

    def __init__(self, response: FakeMinioObjectResponse) -> None:
        """Store configured response."""
        self.response = response
        self.calls: list[dict[str, str]] = []

    def get_object(self, bucket_name: str, object_name: str) -> FakeMinioObjectResponse:
        """Return configured response and capture observable request shape."""
        self.calls.append({"bucket_name": bucket_name, "object_name": object_name})
        return self.response


def _minio_provider(endpoint: str) -> LibrarianProvider:
    now = datetime.now(UTC)
    return LibrarianProvider(
        id="provider-1",
        name="local minio",
        provider_type="MINIO",
        auth_type="API_KEY",
        enabled=True,
        config={"endpoint": endpoint, "bucket": "archive", "prefix": "skills/"},
        created_at=now,
        updated_at=now,
    )


def _sdk_object(name: str, size: int = 42) -> SdkMinioObject:
    return SdkMinioObject(
        bucket_name="archive",
        object_name=name,
        last_modified=datetime(2026, 1, 2, tzinfo=UTC),
        etag="etag-1",
        size=size,
    )


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://169.254.169.254/latest/meta-data",
        "ftp://object.example.com/archive",
        "http://user:pass@objects.example.com",
        "https://objects.example.com/archive",
        "https://objects.example.com?bucket=archive",
    ],
)
def test_minio_endpoint_rejects_malformed_or_sensitive_targets(endpoint: str) -> None:
    """MINIO listing rejects URL shapes that should not reach the SDK boundary."""
    validated = validate_minio_endpoint(endpoint)

    assert validated is None


def test_minio_endpoint_allows_user_supplied_private_address() -> None:
    """User-entered MINIO endpoints may point to local/private object storage."""
    validated = validate_minio_endpoint("http://127.0.0.1:9000")

    assert validated == MinioEndpoint(
        scheme="http",
        host="127.0.0.1",
        port=9000,
        connect_host="127.0.0.1",
    )


def test_minio_endpoint_keeps_link_local_rejected() -> None:
    """Metadata/link-local endpoints remain blocked."""
    validated = validate_minio_endpoint("http://169.254.169.254")

    assert validated is None


def test_minio_endpoint_allows_public_hostname_when_all_answers_are_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Allowlisted public hostnames are resolved before the SDK boundary is reached."""
    monkeypatch.setattr(
        "app.platform.storage.minio_endpoint_safety.socket.getaddrinfo",
        lambda *args, **kwargs: [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", 443),
            )
        ],
    )

    validated = validate_minio_endpoint("https://objects.example.com")

    assert validated == MinioEndpoint(
        scheme="https",
        host="objects.example.com",
        port=None,
        connect_host="93.184.216.34",
    )


def test_minio_endpoint_rejects_hostname_with_link_local_dns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DNS names must not tunnel through to link-local metadata addresses."""
    monkeypatch.setattr(
        "app.platform.storage.minio_endpoint_safety.socket.getaddrinfo",
        lambda *args, **kwargs: [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", 443),
            ),
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("169.254.169.254", 443),
            ),
        ],
    )

    validated = validate_minio_endpoint("https://objects.example.com")

    assert validated is None


def test_pinned_pool_manager_dials_validated_connect_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pinned SDK transport must not re-resolve the original request hostname."""
    connected_targets: list[tuple[str, int]] = []

    def fake_create_connection(
        address: tuple[str, int],
        timeout: object = None,
        source_address: tuple[str, int] | None = None,
        socket_options: object = None,
    ) -> None:
        connected_targets.append(address)
        raise OSError("stop before real network")

    monkeypatch.setattr(
        "urllib3.util.connection.create_connection",
        fake_create_connection,
    )
    transport = PinnedPoolManager(connect_host="93.184.216.34")

    with pytest.raises(NewConnectionError):
        transport.request(
            "GET",
            "http://objects.example.com:9000/archive",
            retries=False,
        )

    assert connected_targets == [("93.184.216.34", 9000)]


def test_minio_listing_returns_bounded_object_metadata_with_sdk_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Object listing uses the SDK boundary and returns normalized metadata."""
    fake_client = FakeMinioClient(
        [_sdk_object("skills/a.md", 7), _sdk_object("skills/b.md", 8)]
    )
    monkeypatch.setattr(
        "app.platform.storage.minio_endpoint_safety.socket.getaddrinfo",
        lambda *args, **kwargs: [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", 443),
            )
        ],
    )
    listing_client = MinioObjectListingClient(
        client_builder=lambda **kwargs: fake_client,
    )

    objects = listing_client.list_objects(
        endpoint="https://objects.example.com",
        bucket="archive",
        prefix="skills/",
        region="us-east-1",
        access_key="access",
        secret_key="secret",
        limit=1,
    )

    assert len(objects) == 1
    assert objects[0].key == "skills/a.md"
    assert objects[0].size == 7
    assert fake_client.calls == [
        {"bucket_name": "archive", "prefix": "skills/", "recursive": True}
    ]


def test_minio_content_reader_returns_bounded_text_and_releases_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Object content reads stay bounded and return SDK responses to the pool."""
    monkeypatch.setattr(
        "app.platform.storage.minio_endpoint_safety.socket.getaddrinfo",
        lambda *args, **kwargs: [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", 443),
            )
        ],
    )
    response = FakeMinioObjectResponse("한글 markdown body".encode())
    fake_client = FakeMinioContentClient(response)

    def fake_builder(**kwargs: object) -> FakeMinioContentClient:
        return fake_client

    content_client = MinioObjectContentClient(
        client_builder=cast(MinioClientBuilder, fake_builder),
    )

    content = content_client.read_text_object(
        endpoint="https://objects.example.com",
        bucket="archive",
        object_key="skills/a.md",
        region="us-east-1",
        access_key="access",
        secret_key="secret",
        max_bytes=8,
    )

    assert content == "한글 m"
    assert response.read_sizes == [9]
    assert response.closed is True
    assert response.released is True
    assert fake_client.calls == [
        {"bucket_name": "archive", "object_name": "skills/a.md"}
    ]
