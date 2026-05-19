"""Pruning contracts for removed synchronous librarian legacy operations."""

from __future__ import annotations

from app.main import app
from fastapi.testclient import TestClient


def test_legacy_sync_librarian_operation_routes_are_not_registered() -> None:
    """Synchronous recommend/classify/create-candidate routes should stay pruned."""
    registered_paths = {getattr(route, "path", "") for route in app.routes}

    assert "/librarians/recommend" not in registered_paths
    assert "/librarians/classify" not in registered_paths
    assert "/librarians/create-skill-candidate" not in registered_paths


def test_legacy_sync_librarian_operation_routes_return_404() -> None:
    """Removed legacy operation routes should not remain callable HTTP surfaces."""
    with TestClient(app, raise_server_exceptions=False) as client:
        responses = [
            client.post(
                "/librarians/recommend",
                json={"query": "fastapi", "item_type": "SKILL", "limit": 1},
            ),
            client.post(
                "/librarians/classify",
                json={"text": "build a reusable API skill"},
            ),
            client.post(
                "/librarians/create-skill-candidate",
                json={"provider_id": "provider-1", "prompt": "Need a browser skill"},
            ),
        ]

    assert [response.status_code for response in responses] == [404, 404, 404]
