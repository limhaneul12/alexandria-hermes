"""Lifecycle readiness HTTP status helpers."""

from __future__ import annotations

from app.platform.lifecycle.snapshot import LifecycleSnapshot
from fastapi import status as http_status


def status_code_from_snapshot(snapshot: LifecycleSnapshot) -> int:
    """Determine HTTP status code from a readiness snapshot.

    Args:
        snapshot: Lifecycle snapshot.

    Returns:
        HTTP status code for readiness endpoints.
    """
    if snapshot.ready:
        status_code = http_status.HTTP_200_OK
        return status_code

    status_code = http_status.HTTP_503_SERVICE_UNAVAILABLE
    return status_code
