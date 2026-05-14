"""Pinned urllib3 transport for validated MINIO hostnames."""

from __future__ import annotations

import logging
import socket
from typing import TYPE_CHECKING, Any, cast

from urllib3 import PoolManager
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool

if TYPE_CHECKING:
    from urllib3._base_connection import BaseHTTPConnection, BaseHTTPSConnection
else:
    BaseHTTPConnection = HTTPConnection
    BaseHTTPSConnection = HTTPSConnection

logger = logging.getLogger(__name__)


class PinnedHTTPConnection(HTTPConnection):
    """HTTP connection that dials a validated IP while preserving Host."""

    # Any justified: urllib3 connection subclasses expose variadic constructor seams.
    def __init__(self, *args: Any, connect_host: str, **kwargs: Any) -> None:
        """Store the validated connection target."""
        super().__init__(*args, **kwargs)
        self._connect_host = connect_host

    def _new_conn(self) -> socket.socket:
        """Open the TCP connection to the prevalidated address."""
        original_dns_host = self._dns_host
        self._dns_host = self._connect_host
        try:
            sock = super()._new_conn()
        finally:
            self._dns_host = original_dns_host
        return sock


class PinnedHTTPSConnection(HTTPSConnection):
    """HTTPS connection that dials a validated IP while preserving SNI/cert host."""

    # Any justified: urllib3 connection subclasses expose variadic constructor seams.
    def __init__(self, *args: Any, connect_host: str, **kwargs: Any) -> None:
        """Store the validated connection target."""
        super().__init__(*args, **kwargs)
        self._connect_host = connect_host

    def _new_conn(self) -> socket.socket:
        """Open the TCP connection to the prevalidated address."""
        original_dns_host = self._dns_host
        self._dns_host = self._connect_host
        try:
            sock = super()._new_conn()
        finally:
            self._dns_host = original_dns_host
        return sock


class PinnedHTTPConnectionPool(HTTPConnectionPool):
    """HTTP pool using a validated connect host."""

    # Any justified: urllib3 pool subclasses expose variadic constructor seams.
    def __init__(self, *args: Any, connect_host: str, **kwargs: Any) -> None:
        """Store the validated connection target."""
        self._connect_host = connect_host
        super().__init__(*args, **kwargs)

    def _new_conn(self) -> BaseHTTPConnection:
        """Create a pinned HTTP connection."""
        self.num_connections += 1
        logger.debug(
            "Starting pinned HTTP connection (%d): %s:%s via %s",
            self.num_connections,
            self.host,
            self.port or "80",
            self._connect_host,
        )
        connection = PinnedHTTPConnection(
            host=self.host,
            port=self.port,
            timeout=self.timeout.connect_timeout,
            connect_host=self._connect_host,
            **self.conn_kw,
        )
        pinned_connection = cast(BaseHTTPConnection, connection)
        return pinned_connection


class PinnedHTTPSConnectionPool(HTTPSConnectionPool):
    """HTTPS pool using a validated connect host."""

    # Any justified: urllib3 pool subclasses expose variadic constructor seams.
    def __init__(self, *args: Any, connect_host: str, **kwargs: Any) -> None:
        """Store the validated connection target."""
        self._connect_host = connect_host
        super().__init__(*args, **kwargs)

    def _new_conn(self) -> BaseHTTPSConnection:
        """Create a pinned HTTPS connection."""
        self.num_connections += 1
        logger.debug(
            "Starting pinned HTTPS connection (%d): %s:%s via %s",
            self.num_connections,
            self.host,
            self.port or "443",
            self._connect_host,
        )
        connection = PinnedHTTPSConnection(
            host=self.host,
            port=self.port,
            timeout=self.timeout.connect_timeout,
            connect_host=self._connect_host,
            **self.conn_kw,
        )
        pinned_connection = cast(BaseHTTPSConnection, connection)
        return pinned_connection


class PinnedPoolManager(PoolManager):
    """Pool manager that pins TCP dial target after endpoint validation."""

    # Any justified: urllib3 PoolManager accepts transport-specific keyword settings.
    def __init__(self, *, connect_host: str, **kwargs: Any) -> None:
        """Configure pinned HTTP and HTTPS pool classes."""
        super().__init__(**kwargs)
        self._connect_host = connect_host
        self.pool_classes_by_scheme = {
            "http": PinnedHTTPConnectionPool,
            "https": PinnedHTTPSConnectionPool,
        }

    def _new_pool(
        self,
        scheme: str,
        host: str,
        port: int,
        # Any justified: urllib3 passes dynamic request-context keys through this override.
        request_context: dict[str, Any] | None = None,
    ) -> HTTPConnectionPool:
        """Create a pool with the validated connect host injected."""
        active_context = {} if request_context is None else request_context.copy()
        active_context["connect_host"] = self._connect_host
        pool = super()._new_pool(
            scheme=scheme,
            host=host,
            port=port,
            request_context=active_context,
        )
        return pool
