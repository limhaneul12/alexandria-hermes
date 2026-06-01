"""Contracts proving broad legacy library-style route namespaces stay removed."""

from __future__ import annotations

import pytest
from app.main import app
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    "path",
    [
        "/library",
        "/library/items",
        "/skills",
        "/prompts",
        "/usage",
        "/categories",
    ],
)
def test_legacy_library_route_namespaces_are_not_registered(path: str) -> None:
    """Removed SQLite library CRUD namespaces should not be public routes."""
    assert path not in app.openapi()["paths"]


@pytest.mark.parametrize(
    "path",
    [
        "/library",
        "/library/items",
        "/skills",
        "/prompts",
        "/usage",
        "/categories",
    ],
)
def test_legacy_library_route_namespaces_return_404(path: str) -> None:
    """Removed library CRUD routes should fail before dependency resolution."""
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(path)

    assert response.status_code == 404
