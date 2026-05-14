"""MINIO object content adapter backed by the official MinIO SDK."""

from __future__ import annotations

from collections.abc import Callable

from app.platform.storage.minio_client_factory import build_minio_client
from app.platform.storage.minio_endpoint_safety import validate_minio_endpoint
from app.platform.storage.minio_object_listing import DEFAULT_REGION
from app.platform.storage.minio_types import MinioEndpoint
from minio import Minio

MAX_MINIO_TEXT_BYTES = 128 * 1024

MinioClientBuilder = Callable[..., Minio]


class MinioObjectContentClient:
    """Read object text content from MINIO after endpoint validation."""

    def __init__(
        self,
        *,
        client_builder: MinioClientBuilder = build_minio_client,
    ) -> None:
        """Store dependencies for SDK-backed content reads."""
        self._client_builder = client_builder

    def read_text_object(
        self,
        *,
        endpoint: str,
        bucket: str,
        object_key: str,
        region: str = DEFAULT_REGION,
        access_key: str,
        secret_key: str,
        max_bytes: int = MAX_MINIO_TEXT_BYTES,
    ) -> str:
        """Read bounded UTF-8 text content from one MINIO object.

        Args:
            endpoint: MINIO endpoint URL.
            bucket: Bucket containing the object.
            object_key: Object key to read.
            region: MINIO region supplied to the SDK.
            access_key: Access key credential.
            secret_key: Secret key credential.
            max_bytes: Maximum bytes to read before decoding.

        Returns:
            Decoded text content capped to ``max_bytes``.
        """
        bounded_max_bytes = max(1, min(max_bytes, MAX_MINIO_TEXT_BYTES))
        validated_endpoint = validate_minio_endpoint(endpoint)
        if validated_endpoint is None:
            raise ValueError("MINIO endpoint is not allowed")
        client = self._build_client(
            endpoint=validated_endpoint,
            access_key=access_key,
            secret_key=secret_key,
            region=region,
        )
        response = client.get_object(bucket, object_key)
        try:
            data = response.read(bounded_max_bytes + 1)
        finally:
            response.close()
            response.release_conn()
        text = data[:bounded_max_bytes].decode("utf-8", errors="replace")
        return text

    def _build_client(
        self,
        *,
        endpoint: MinioEndpoint,
        access_key: str,
        secret_key: str,
        region: str,
    ) -> Minio:
        """Build the SDK client through the injected factory."""
        client = self._client_builder(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            region=region,
        )
        return client
