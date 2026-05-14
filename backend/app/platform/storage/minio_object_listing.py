"""MINIO object listing adapter backed by the official MinIO SDK."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, datetime

from app.platform.storage.minio_client_factory import build_minio_client
from app.platform.storage.minio_endpoint_safety import validate_minio_endpoint
from app.platform.storage.minio_types import MinioObject
from minio import Minio
from minio.datatypes import Object as SdkMinioObject

DEFAULT_REGION = "us-east-1"
MAX_MINIO_LIST_LIMIT = 1000

MinioClientBuilder = Callable[..., Minio]


class MinioObjectListingClient:
    """List objects from MINIO after validating the server-side endpoint."""

    def __init__(
        self,
        *,
        client_builder: MinioClientBuilder = build_minio_client,
    ) -> None:
        """Store dependencies for SDK-backed object listing."""
        self._client_builder = client_builder

    def list_objects(
        self,
        *,
        endpoint: str,
        bucket: str,
        prefix: str,
        region: str,
        access_key: str,
        secret_key: str,
        limit: int,
    ) -> list[MinioObject]:
        """List object metadata using the official MinIO SDK.

        Args:
            endpoint [str]: Value supplied to list_objects.
            bucket [str]: Value supplied to list_objects.
            prefix [str]: Value supplied to list_objects.
            region [str]: Value supplied to list_objects.
            access_key [str]: Value supplied to list_objects.
            secret_key [str]: Value supplied to list_objects.
            limit [int]: Value supplied to list_objects.

        Returns:
            list[MinioObject]: Value produced by list_objects.
        """
        validated_endpoint = validate_minio_endpoint(endpoint)
        if validated_endpoint is None:
            return []
        bounded_limit = max(1, min(limit, MAX_MINIO_LIST_LIMIT))
        client = self._client_builder(
            endpoint=validated_endpoint,
            access_key=access_key,
            secret_key=secret_key,
            region=region or DEFAULT_REGION,
        )
        sdk_objects = client.list_objects(
            bucket,
            prefix=prefix or None,
            recursive=True,
        )
        objects = list(_limit(_map_sdk_objects(sdk_objects), bounded_limit))
        return objects


def _map_sdk_objects(
    sdk_objects: Iterable[SdkMinioObject],
) -> Iterable[MinioObject]:
    for sdk_object in sdk_objects:
        key = sdk_object.object_name or ""
        if not key:
            continue
        last_modified = sdk_object.last_modified or datetime.now(UTC)
        yield MinioObject(
            key=key,
            size=sdk_object.size or 0,
            etag=sdk_object.etag or "",
            last_modified=last_modified,
        )


def _limit(values: Iterable[MinioObject], limit: int) -> Iterable[MinioObject]:
    for index, value in enumerate(values):
        if index >= limit:
            break
        yield value
