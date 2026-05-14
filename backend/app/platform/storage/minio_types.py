"""Typed contracts for MINIO platform storage integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class MinioEndpoint:
    """Validated MINIO endpoint details."""

    scheme: str
    host: str
    port: int | None
    connect_host: str

    @property
    def secure(self) -> bool:
        """Return whether the endpoint uses TLS.

        Returns:
            bool: Value produced by secure.
        """
        secure = self.scheme == "https"
        return secure

    @property
    def client_endpoint(self) -> str:
        """Return endpoint form expected by the official MinIO SDK.

        Returns:
            str: Value produced by client_endpoint.
        """
        if self.port is None:
            endpoint = self.host
        else:
            endpoint = f"{self.host}:{self.port}"
        return endpoint


@dataclass(frozen=True, slots=True)
class MinioObject:
    """Object metadata returned by a MINIO/S3 list operation."""

    key: str
    size: int
    etag: str
    last_modified: datetime
