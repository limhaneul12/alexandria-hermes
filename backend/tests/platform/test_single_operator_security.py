"""Single-operator security contract tests."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.main import app
from app.platform.security.operator_api_key import (
    OPERATOR_API_KEY_HEADER,
    require_operator_api_key,
)
from fastapi.testclient import TestClient
from tests.shared.provider_overrides import override_library_provider

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent
TEST_OPERATOR_API_KEY = "test-operator-api-key-for-route-contracts-000000000000"


class EmptyLibrarianProviderService:
    """Fake settings service for protected-route policy tests."""

    async def list_providers(self) -> list[object]:
        """Return no configured provider rows.

        Returns:
            Empty provider list.
        """
        return []


@contextmanager
def enforce_operator_api_key_dependency() -> Iterator[None]:
    """Temporarily restore the real operator auth dependency.

    Yields:
        None.
    """
    previous_override = app.dependency_overrides.pop(require_operator_api_key, None)
    try:
        yield
    finally:
        if previous_override is not None:
            app.dependency_overrides[require_operator_api_key] = previous_override


def test_control_plane_route_rejects_missing_and_wrong_operator_key() -> None:
    """Control-plane settings routes require the configured operator key."""
    with (
        enforce_operator_api_key_dependency(),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        missing = client.get("/settings/connections")
        wrong = client.get(
            "/settings/connections",
            headers={OPERATOR_API_KEY_HEADER: "wrong-operator-key"},
        )

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert missing.json() == {"detail": "Operator API key required"}
    assert wrong.json() == {"detail": "Operator API key required"}


def test_control_plane_route_accepts_configured_operator_key() -> None:
    """Control-plane settings routes reach service logic with the operator key."""
    service = EmptyLibrarianProviderService()

    with (
        override_library_provider("librarian_service", service),
        enforce_operator_api_key_dependency(),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.get(
            "/settings/connections",
            headers={OPERATOR_API_KEY_HEADER: TEST_OPERATOR_API_KEY},
        )

    assert response.status_code == 200
    assert response.json() == []


def test_health_routes_remain_public_without_operator_key() -> None:
    """Public health routes should not require operator credentials."""
    with (
        enforce_operator_api_key_dependency(),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        live = client.get("/health/live")
        ready = client.get("/health/ready")

    assert live.status_code == 200
    assert ready.status_code == 200


def test_backend_app_has_no_direct_environment_reads() -> None:
    """Application code should use typed config/Typer boundaries for env values."""
    offenders = sorted(
        str(path.relative_to(BACKEND_ROOT))
        for path in (BACKEND_ROOT / "app").rglob("*.py")
        if "os.environ" in path.read_text(encoding="utf-8")
        or "os.getenv" in path.read_text(encoding="utf-8")
    )

    assert offenders == []


def test_active_code_and_onboarding_docs_do_not_use_legacy_api_token() -> None:
    """Active code/docs should not revive the legacy Alexandria API-token model."""
    legacy_token_name = "ALEXANDRIA_" + "API_TOKEN"
    checked_roots = [
        BACKEND_ROOT / "app",
        REPO_ROOT / "install.md",
        REPO_ROOT / "README.md",
        REPO_ROOT / "docker-compose.yml",
        REPO_ROOT / "docs" / "usage_guidebook",
    ]
    offenders: list[str] = []
    for root in checked_roots:
        paths = [root] if root.is_file() else sorted(root.rglob("*"))
        for path in paths:
            if not path.is_file() or path.suffix not in {
                ".py",
                ".ts",
                ".tsx",
                ".md",
                ".yml",
            }:
                continue
            if legacy_token_name in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(REPO_ROOT)))

    assert offenders == []


def test_compose_defaults_bind_service_ports_to_localhost() -> None:
    """Docker Compose defaults should avoid accidental LAN/public exposure."""
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert '"127.0.0.1:8000:8000"' in compose
    assert "3000:3000" not in compose
    assert "frontend" not in compose
