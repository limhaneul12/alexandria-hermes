"""Contracts proving MINIO archive import surfaces stay removed from core."""

from __future__ import annotations

from app.main import app


def test_minio_archive_routes_are_not_registered() -> None:
    """Object-storage import routes must not remain in the public API."""
    minio_paths = [
        path for path in app.openapi()["paths"] if path.startswith("/archive/minio")
    ]

    assert minio_paths == []
