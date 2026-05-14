import uuid

from app.main import app
from fastapi.testclient import TestClient


def test_health_live() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_x_trace_id_generated_when_missing() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live")
        trace_id = response.headers.get("x-trace-id")
        assert trace_id is not None
        parsed_trace_id = uuid.UUID(trace_id)
        assert parsed_trace_id.version == 4


def test_x_trace_id_passthrough_when_provided() -> None:
    with TestClient(app) as client:
        custom_trace_id = "0191f3c7-1111-4aa3-8000-0123456789ab"

        response = client.get(
            "/health/live",
            headers={"x-trace-id": custom_trace_id, "x-request-id": "REQ-42"},
        )

        assert response.headers.get("x-trace-id") == custom_trace_id


def test_health_live_ready_heartbeat() -> None:
    with TestClient(app) as client:
        live_response = client.get("/health/live")
        assert live_response.status_code == 200
        assert live_response.json() == {"status": "ok"}

        ready_response = client.get("/health/ready")
        assert ready_response.status_code == 200
        ready_payload = ready_response.json()
        assert ready_payload["status"] == "ok"
        assert ready_payload["checks"]["app"] == "ok"
        assert ready_payload["checks"]["redis"] == "disabled"
        assert ready_payload["checks"]["database"] == "ok"
        assert ready_payload["checks"]["minio"] == "disabled"

        heartbeat_response = client.get("/health/heartbeat")
        assert heartbeat_response.status_code == 200
        heartbeat_payload = heartbeat_response.json()
        assert heartbeat_payload["heartbeat"]["lifecycle"] == "running"
        assert heartbeat_payload["heartbeat"]["app"] == "ok"
        assert heartbeat_payload["heartbeat"]["redis"] == "disabled"
        assert heartbeat_payload["heartbeat"]["database"] == "ok"
        assert heartbeat_payload["heartbeat"]["minio"] == "disabled"
