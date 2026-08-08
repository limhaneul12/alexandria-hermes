"""HTTP boundary contracts for queued embedding reindex work."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_legacy_direct_embedding_reindex_route_requires_the_redis_queue() -> None:
    """Public callers must not bypass the bounded maintenance worker."""
    with TestClient(app) as client:
        response = client.post(
            "/memory/contexts/retrieval/reindex",
            params={"limit": 250, "force": "false"},
        )

    assert response.status_code == 409
    assert response.json() == {
        "detail": {
            "error_code": "EMBEDDING_REINDEX_REQUIRES_QUEUE",
            "message": (
                "Embedding reindex must be submitted to the bounded Redis "
                "Streams maintenance queue."
            ),
            "submission_endpoint": ("/operations/maintenance/embedding-reindex/jobs"),
        }
    }
