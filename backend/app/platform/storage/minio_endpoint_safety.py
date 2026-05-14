"""Endpoint safety checks for server-side MINIO access."""

from __future__ import annotations

import ipaddress
import socket
import urllib.parse

from app.platform.storage.minio_types import MinioEndpoint


def validate_minio_endpoint(endpoint: str) -> MinioEndpoint | None:
    """Validate one MINIO endpoint before any SDK network access.

    Args:
        endpoint [str]: Value supplied to validate_minio_endpoint.

    Returns:
        MinioEndpoint | None: Value produced by validate_minio_endpoint.
    """
    parsed = urllib.parse.urlparse(endpoint.rstrip("/"))
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        return None
    try:
        port = parsed.port
    except ValueError:
        return None
    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        return None
    validation_port = port or (443 if parsed.scheme == "https" else 80)
    safe_connect_host = _validated_connect_host(
        hostname=hostname,
        port=validation_port,
    )
    if safe_connect_host is None:
        return None
    endpoint_contract = MinioEndpoint(
        scheme=parsed.scheme,
        host=hostname,
        port=port,
        connect_host=safe_connect_host,
    )
    return endpoint_contract


def _validated_connect_host(
    *,
    hostname: str,
    port: int,
) -> str | None:
    try:
        literal_address = ipaddress.ip_address(hostname)
    except ValueError:
        connect_host = _validated_resolved_connect_host(
            hostname=hostname,
            port=port,
        )
    else:
        if not _is_connectable_address_allowed(literal_address):
            return None
        connect_host = str(literal_address)
    return connect_host


def _validated_resolved_connect_host(
    *,
    hostname: str,
    port: int,
) -> str | None:
    try:
        infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except OSError:
        return None
    safe_connect_host: str | None = None
    for _family, _type, _proto, _canonname, sockaddr in infos:
        if not sockaddr:
            return None
        try:
            address = ipaddress.ip_address(str(sockaddr[0]))
        except ValueError:
            return None
        if not _is_connectable_address_allowed(address):
            return None
        if safe_connect_host is None:
            safe_connect_host = str(address)
    return safe_connect_host


def _is_connectable_address_allowed(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> bool:
    if address.is_link_local or address.is_multicast or address.is_unspecified:
        return False
    if address.is_reserved:
        return False
    return address.is_loopback or address.is_private or address.is_global
