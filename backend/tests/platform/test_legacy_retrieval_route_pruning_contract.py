"""Contracts proving legacy retrieval metadata/search routes stay removed."""

from __future__ import annotations

import pytest
from app.main import app
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    "path",
    [
        "/retrieval/search",
        "/retrieval/search/library/skills",
        "/retrieval/search/library/knowledge",
        "/retrieval/boundary/modes",
    ],
)
def test_legacy_retrieval_routes_are_not_registered(path: str) -> None:
    """Legacy retrieval routes should not remain in the public API surface."""
    assert path not in app.openapi()["paths"]


@pytest.mark.parametrize(
    "path",
    [
        "/retrieval/search?q=test",
        "/retrieval/search/library/skills?q=test",
        "/retrieval/search/library/knowledge?q=test",
        "/retrieval/boundary/modes",
    ],
)
def test_legacy_retrieval_routes_return_404(path: str) -> None:
    """Removed retrieval routes should fail before touching any service dependency."""
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(path)

    assert response.status_code == 404
