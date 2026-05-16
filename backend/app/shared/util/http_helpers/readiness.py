"""Lifecycle readiness HTTP status helpers."""

from __future__ import annotations

from fastapi import status as http_status


def status_code_from_ready(ready: bool) -> int:
    """Determine HTTP status code from readiness state.

    Args:
        ready: Whether the service is ready to receive traffic.

    Returns:
        HTTP status code for readiness endpoints.
    """
    if ready:
        status_code = http_status.HTTP_200_OK
        return status_code

    status_code = http_status.HTTP_503_SERVICE_UNAVAILABLE
    return status_code
