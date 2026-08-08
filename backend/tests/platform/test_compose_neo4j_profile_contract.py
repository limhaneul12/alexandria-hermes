"""Docker Compose contract for the Neo4j graph read-model service."""

import os
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _compose_text() -> str:
    return (REPOSITORY_ROOT / "docker-compose.yml").read_text(encoding="utf-8")


def _shared_compose_text() -> str:
    return (REPOSITORY_ROOT / "env-compose.yml").read_text(encoding="utf-8")


def _neo4j_start_path() -> Path:
    return REPOSITORY_ROOT / "scripts" / "neo4j-start.sh"


def test_compose_declares_explicit_alexandria_service_names() -> None:
    """The graph container should use the explicit Alexandria service names."""
    compose = _compose_text()

    assert "  alexandria-backend:" in compose
    assert "container_name: alexandria-backend" in compose
    assert "  alexandria-graph:" in compose
    assert "container_name: alexandria-graph" in compose
    assert "neo4j:5-community" in compose
    assert "alexandria-network" in compose


def test_compose_starts_graph_with_the_default_topology() -> None:
    """Neo4j must start with the normal Compose application topology."""
    compose = _compose_text()
    graph_start = compose.index("  alexandria-graph:")
    graph_end = compose.index("\nvolumes:", graph_start)
    graph_service = compose[graph_start:graph_end]

    assert "profiles:" not in graph_service


def test_compose_exposes_neo4j_network_alias() -> None:
    """Operator-local bolt://neo4j:7687 URIs must resolve inside Compose."""
    compose = _compose_text()
    graph_start = compose.index("  alexandria-graph:")
    graph_end = compose.index("\nvolumes:", graph_start)
    graph_service = compose[graph_start:graph_end]

    assert "aliases:" in graph_service
    assert "- neo4j" in graph_service


def test_compose_persists_neo4j_data_and_logs() -> None:
    """Graph projection data should survive restarts without touching the vault."""
    compose = _compose_text()

    assert "neo4j-data:/data" in compose
    assert "neo4j-logs:/logs" in compose
    assert "volumes:" in compose
    assert "neo4j-data:" in compose
    assert "neo4j-logs:" in compose


def test_compose_neo4j_password_has_no_tracked_fallback() -> None:
    """Compose and the startup script must not provide a password fallback."""
    compose = _compose_text()
    script = _neo4j_start_path().read_text(encoding="utf-8")

    assert (
        ': "${ALEXANDRIA_NEO4J_PASSWORD:?ALEXANDRIA_NEO4J_PASSWORD is required}"'
    ) in script
    assert 'case "${ALEXANDRIA_NEO4J_PASSWORD}" in' in script
    assert "ALEXANDRIA_NEO4J_PASSWORD must not be blank" in script
    assert 'export NEO4J_AUTH="neo4j/${ALEXANDRIA_NEO4J_PASSWORD}"' in script
    assert "ALEXANDRIA_NEO4J_PASSWORD:-" not in compose
    assert "ALEXANDRIA_NEO4J_PASSWORD:-" not in script
    assert "NEO4J_AUTH: neo4j/${ALEXANDRIA_NEO4J_PASSWORD" not in compose
    assert "command:\n      - |" not in compose


def test_neo4j_startup_script_rejects_blank_password() -> None:
    """The graph startup script must fail closed for blank-looking secrets."""
    env = {"PATH": os.environ["PATH"], "ALEXANDRIA_NEO4J_PASSWORD": "    "}

    result = subprocess.run(
        ["/bin/sh", str(_neo4j_start_path())],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "ALEXANDRIA_NEO4J_PASSWORD must not be blank" in result.stderr


def test_compose_backend_reads_graph_runtime_configuration_from_env_file() -> None:
    """Backend Neo4j runtime values belong in the operator-local .env file."""
    compose = _compose_text()
    shared = _shared_compose_text()

    assert "env_file:" in shared
    assert "- ./.env" in shared
    assert "file: ./env-compose.yml" in compose
    assert "SERVICE_NEO4J_URI:" not in compose
    assert "SERVICE_NEO4J_USERNAME:" not in compose
    assert "SERVICE_NEO4J_PASSWORD:" not in compose
    assert "SERVICE_NEO4J_DATABASE:" not in compose
    assert "SERVICE_NEO4J_PASSWORD:-" not in compose
