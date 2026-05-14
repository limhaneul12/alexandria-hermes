"""List MINIO-backed archive items."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable

from app.library.application.mappers.minio_archive_mapper import (
    map_minio_object_to_archive_item,
)
from app.library.domain.contracts.minio_archive_contracts import MinioArchiveItem
from app.library.domain.entities.read_models import LibrarianProvider
from app.library.domain.repositories.librarian_repository import (
    ILibrarianProviderRepository,
    IProviderSecretRepository,
)
from app.platform.storage.minio_object_listing import (
    DEFAULT_REGION,
    MAX_MINIO_LIST_LIMIT,
    MinioObjectListingClient,
)
from app.shared.types.types_convert_utils import bool_value, string_value
from minio.error import S3Error
from urllib3.exceptions import HTTPError

MINIO_PROVIDER_TYPE = "MINIO"


class ListMinioArchiveItemsUseCase:
    """List MINIO archive objects through library provider configuration."""

    def __init__(
        self,
        provider_repo: ILibrarianProviderRepository,
        secret_repo: IProviderSecretRepository,
    ) -> None:
        """Initialize use case dependencies."""
        self.provider_repo = provider_repo
        self.secret_repo = secret_repo

    async def execute(self, limit: int) -> list[MinioArchiveItem]:
        """List MINIO-backed archive items from enabled MINIO providers.

        Args:
            limit: Maximum number of archive items to return after bounding.

        Returns:
            list[MinioArchiveItem]: Archive items normalized from MINIO listings.
        """
        bounded_limit = max(1, min(limit, MAX_MINIO_LIST_LIMIT))
        listing_client = MinioObjectListingClient()
        providers = [
            provider
            for provider in await self.provider_repo.list_all()
            if provider.enabled and provider.provider_type == MINIO_PROVIDER_TYPE
        ]
        archive_items: list[MinioArchiveItem] = []
        for provider in providers:
            provider_items = await self._list_provider_items(
                provider=provider,
                listing_client=listing_client,
                limit=bounded_limit,
            )
            archive_items.extend(provider_items)
        limited_items = list(_limit(archive_items, bounded_limit))
        return limited_items

    async def _list_provider_items(
        self,
        provider: LibrarianProvider,
        listing_client: MinioObjectListingClient,
        limit: int,
    ) -> list[MinioArchiveItem]:
        """List normalized archive items for one configured MINIO provider."""
        endpoint = string_value(provider.config.get("endpoint")).strip()
        bucket = string_value(provider.config.get("bucket")).strip()
        prefix = string_value(provider.config.get("prefix")).strip()
        region = (
            string_value(provider.config.get("region"), default=DEFAULT_REGION).strip()
            or DEFAULT_REGION
        )
        if bool_value(provider.config.get("use_ssl")) and endpoint.startswith(
            "http://"
        ):
            endpoint = "https://" + endpoint.removeprefix("http://")
        secret = await self.secret_repo.resolve(provider.id, "api_key")
        secret_pair = _split_minio_secret(secret or "")
        if not endpoint or not bucket or secret_pair is None:
            return []
        access_key, secret_key = secret_pair
        try:
            objects = await asyncio.to_thread(
                listing_client.list_objects,
                endpoint=endpoint,
                bucket=bucket,
                prefix=prefix,
                region=region,
                access_key=access_key,
                secret_key=secret_key,
                limit=limit,
            )
        except (OSError, ValueError, S3Error, HTTPError):
            return []
        archive_items = [
            map_minio_object_to_archive_item(
                provider=provider,
                bucket=bucket,
                endpoint=endpoint,
                item=item,
            )
            for item in objects
        ]
        return archive_items


def _split_minio_secret(secret: str) -> tuple[str, str] | None:
    access_key, separator, secret_key = secret.partition(":")
    if not separator or not access_key.strip() or not secret_key.strip():
        return None
    secret_pair = access_key.strip(), secret_key.strip()
    return secret_pair


def _limit(
    values: Iterable[MinioArchiveItem],
    limit: int,
) -> Iterable[MinioArchiveItem]:
    for index, value in enumerate(values):
        if index >= limit:
            break
        yield value
