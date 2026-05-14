"""Factory for official MinIO SDK clients."""

from __future__ import annotations

from app.platform.storage.minio_pinned_transport import PinnedPoolManager
from app.platform.storage.minio_types import MinioEndpoint
from minio import Minio
from urllib3 import Timeout
from urllib3.util.retry import Retry

MINIO_CONNECT_TIMEOUT_SECONDS = 3.0
MINIO_READ_TIMEOUT_SECONDS = 3.0


def build_minio_client(
    *,
    endpoint: MinioEndpoint,
    access_key: str,
    secret_key: str,
    region: str,
) -> Minio:
    """Build an SDK client with bounded network behavior.

    Args:
        endpoint [MinioEndpoint]: Value supplied to build_minio_client.
        access_key [str]: Value supplied to build_minio_client.
        secret_key [str]: Value supplied to build_minio_client.
        region [str]: Value supplied to build_minio_client.

    Returns:
        Minio: Value produced by build_minio_client.
    """
    timeout = Timeout(
        connect=MINIO_CONNECT_TIMEOUT_SECONDS,
        read=MINIO_READ_TIMEOUT_SECONDS,
    )
    http_client = PinnedPoolManager(
        connect_host=endpoint.connect_host,
        timeout=timeout,
        retries=Retry(total=0, redirect=False),
    )
    client = Minio(
        endpoint.client_endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=endpoint.secure,
        region=region,
        http_client=http_client,
    )
    return client
