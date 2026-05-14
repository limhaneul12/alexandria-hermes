"""Register FastAPI health check endpoints."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.platform.lifecycle.state import LifecycleState
from app.platform.schemas.health_schema import (
    LiveHealthPayload,
    heartbeat_payload_from_snapshot,
    ready_payload_from_snapshot,
)
from app.shared.serialization.model_codec import dumps_model
from app.shared.util.http_helpers.readiness import status_code_from_snapshot
from app.shared.util.http_helpers.response_headers import json_response
from fastapi import FastAPI, status
from fastapi.responses import Response

DependencyHealthRefresher = Callable[[], Awaitable[None]]


def install_health_routes(
    app: FastAPI,
    *,
    lifecycle: LifecycleState,
    refresh_dependency_health: DependencyHealthRefresher | None = None,
) -> None:
    """Register FastAPI health endpoints on the application.

    Args:
        app: FastAPI app where endpoints are registered.
        lifecycle: Process-local lifecycle state.
        refresh_dependency_health: Optional callback to refresh dependency status before ready/heartbeat.

    Returns:
        None.
    """

    @app.get("/health/live")
    def get_health_live() -> Response:
        """Return process liveness health response.

        Args:
            None.

        Returns:
            Return value.
        """
        payload = LiveHealthPayload(status="ok")
        return json_response(
            payload=dumps_model(payload),
            status_code=status.HTTP_200_OK,
        )

    @app.get("/health/ready")
    async def get_health_ready() -> Response:
        """Return readiness status for receiving new traffic.

        Args:
            None.

        Returns:
            Return value.
        """
        if refresh_dependency_health is not None:
            await refresh_dependency_health()
        snapshot = lifecycle.snapshot()
        payload = ready_payload_from_snapshot(snapshot)
        return json_response(
            payload=dumps_model(payload),
            status_code=status_code_from_snapshot(snapshot),
        )

    @app.get("/health/heartbeat")
    async def get_health_heartbeat() -> Response:
        """Return detailed heartbeat status.

        Args:
            None.

        Returns:
            Return value.
        """
        if refresh_dependency_health is not None:
            await refresh_dependency_health()
        snapshot = lifecycle.snapshot()
        payload = heartbeat_payload_from_snapshot(snapshot)
        return json_response(
            payload=dumps_model(payload),
            status_code=status_code_from_snapshot(snapshot),
        )
