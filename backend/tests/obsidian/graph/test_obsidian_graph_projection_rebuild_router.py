"""FastAPI contracts for explicit graph projection rebuild/status operations."""

from __future__ import annotations

from pathlib import Path

import anyio
import pytest
from app.main import app as default_app
from app.main import create_app
from app.obsidian.infrastructure.graph import neo4j_graph_projection_factory
from app.platform.config.app_config import AppConfig
from app.shared.infrastructure.database import Database
from dependency_injector import providers
from fastapi.testclient import TestClient

_ROUTER_PACKAGES = [
    "app.connections.interface.routers",
    "app.librarian.interface.routers",
    "app.memory.interface.routers",
    "app.obsidian.interface.routers",
    "app.operations.interface.routers",
]


def _database_url(path: Path) -> str:
    return f"sqlite+aiosqlite:///{path}"


def test_disabled_projection_rebuild_and_status_api_do_not_create_neo4j_driver_or_vault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default disabled API responses should be explicit and non-mutating."""
    database_url = _database_url(tmp_path / "api.db")
    database = Database(database_url=database_url, create_schema=True)
    anyio.run(database.initialize)
    anyio.run(database.shutdown)
    monkeypatch.setenv("DATABASE_URL", database_url)

    def fail_driver(
        _uri: str,
        *,
        auth: tuple[str, str],
    ) -> object:
        _ = auth
        raise AssertionError("disabled graph API created the Neo4j driver")

    monkeypatch.setattr(
        neo4j_graph_projection_factory.AsyncGraphDatabase,
        "driver",
        staticmethod(fail_driver),
    )
    vault_path = tmp_path / "vault"
    app = create_app(
        AppConfig(
            _env_file=None,
            graph_read_model="disabled",
            obsidian_vault_path=str(vault_path),
            obsidian_vault_config_path=str(tmp_path / "vault-config.json"),
            obsidian_librarian_langgraph_checkpoint_path=str(
                tmp_path / "librarian.sqlite"
            ),
            operational_backup_root=str(tmp_path / "backups"),
        )
    )
    root_container = app.state.container

    try:
        with (
            root_container.librarian.hermes_collaboration_service.override(
                providers.Object(None)
            ),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            status_response = client.get("/obsidian/graph/projection/status")
            rebuild_response = client.post("/obsidian/graph/projection/rebuild")
            related_response = client.get("/obsidian/notes/missing/related")
    finally:
        default_app.state.container.wire(packages=_ROUTER_PACKAGES)

    assert status_response.status_code == 200
    assert status_response.json() == {
        "status": "disabled",
        "graph_read_model": "disabled",
        "enabled": False,
        "node_count": 0,
        "edge_count": 0,
        "run_id": None,
        "projection_version": None,
        "last_run_issue_total": 0,
        "last_run_issue_counts": [],
        "errors": [],
    }
    assert rebuild_response.status_code == 200
    payload = rebuild_response.json()
    assert payload["status"] == "disabled"
    assert payload["graph_read_model"] == "disabled"
    assert payload["scanned"] == 0
    assert payload["indexed"] == 0
    assert payload["updated"] == 0
    assert payload["skipped"] == 0
    assert payload["issue_total"] == 0
    assert payload["issue_counts"] == []
    assert payload["issues"] == []
    assert payload["issues_truncated"] is False
    assert payload["errors"] == []
    assert isinstance(payload["run_id"], str)
    assert payload["duration_seconds"] >= 0.0
    assert related_response.status_code == 503
    assert "disabled" in related_response.json()["detail"]
    assert not vault_path.exists()
