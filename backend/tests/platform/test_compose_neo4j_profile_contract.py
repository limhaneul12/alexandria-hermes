"""Docker Compose contract for optional Neo4j graph read-model service."""

import os
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _compose_text() -> str:
    return (REPOSITORY_ROOT / "docker-compose.yml").read_text(encoding="utf-8")


def _neo4j_entrypoint_script(compose: str) -> str:
    start = compose.index('        : "$${ALEXANDRIA_NEO4J_PASSWORD')
    end = compose.index("    ports:", start)
    lines = compose[start:end].splitlines()
    return "\n".join(line[8:] for line in lines).replace("$$", "$")


def test_compose_declares_neo4j_as_optional_graph_profile() -> None:
    """Neo4j must be opt-in so the default backend startup stays SQLite-only."""
    compose = (REPOSITORY_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "  neo4j:" in compose
    assert "profiles:" in compose
    assert '- "graph"' in compose
    assert "neo4j:5-community" in compose


def test_compose_persists_neo4j_data_in_named_volume() -> None:
    """Graph projection data should survive container restarts without touching the vault."""
    compose = (REPOSITORY_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "neo4j-data:/data" in compose
    assert "neo4j-logs:/logs" in compose
    assert "volumes:" in compose
    assert "neo4j-data:" in compose
    assert "neo4j-logs:" in compose


def test_compose_requires_explicit_neo4j_password_injection() -> None:
    """Tracked Compose must not provide a predictable Neo4j password fallback."""
    compose = _compose_text()

    assert (
        '"$${ALEXANDRIA_NEO4J_PASSWORD:?'
        'set ALEXANDRIA_NEO4J_PASSWORD for the graph profile}"'
    ) in compose
    assert 'case "$${ALEXANDRIA_NEO4J_PASSWORD}" in' in compose
    assert "ALEXANDRIA_NEO4J_PASSWORD must not be blank" in compose
    assert 'export NEO4J_AUTH="neo4j/$${ALEXANDRIA_NEO4J_PASSWORD}"' in compose
    assert "ALEXANDRIA_NEO4J_PASSWORD:-" not in compose
    assert "NEO4J_AUTH: neo4j/${ALEXANDRIA_NEO4J_PASSWORD" not in compose


def test_compose_rejects_whitespace_only_neo4j_password() -> None:
    """The graph profile must fail closed for blank-looking local secrets."""
    compose = _compose_text()
    script = _neo4j_entrypoint_script(compose)
    env = {"PATH": os.environ["PATH"], "ALEXANDRIA_NEO4J_PASSWORD": "    "}

    result = subprocess.run(
        ["/bin/sh", "-eu", "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "ALEXANDRIA_NEO4J_PASSWORD must not be blank" in result.stderr


def test_compose_backend_reads_graph_runtime_configuration_from_env_file() -> None:
    """Backend Neo4j runtime values belong in the operator-local .env file."""
    compose = (REPOSITORY_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "env_file:" in compose
    assert "- ./.env" in compose
    assert "SERVICE_NEO4J_URI:" not in compose
    assert "SERVICE_NEO4J_USERNAME:" not in compose
    assert "SERVICE_NEO4J_PASSWORD:" not in compose
    assert "SERVICE_NEO4J_DATABASE:" not in compose
    assert "SERVICE_NEO4J_PASSWORD:-" not in compose
