"""Regression contract for graceful backend container shutdown."""

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_compose_execs_uvicorn_as_the_container_process() -> None:
    """Compose must forward stop signals instead of leaving Uvicorn behind a shell."""
    compose = (REPOSITORY_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "uv run alembic upgrade head && exec uv run uvicorn app.main:app" in compose
