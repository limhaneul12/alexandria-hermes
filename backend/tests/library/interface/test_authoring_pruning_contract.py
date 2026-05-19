"""Pruning contracts for manual library authoring routes."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from app.main import app
from fastapi.testclient import TestClient
from tests.shared.provider_overrides import override_library_provider


class FailingAuthoringService:
    """Fail if a pruned authoring route still reaches an application service."""

    def __getattr__(self, name: str) -> Callable[..., object]:
        """Return a callable that fails on any accidental service access."""

        def fail(*_args: object, **_kwargs: object) -> object:
            raise AssertionError(f"pruned authoring service method called: {name}")

        return fail


@pytest.mark.parametrize(
    ("provider_name", "path", "payload"),
    [
        (
            "item_service",
            "/library/items",
            {
                "item_type": "PROMPT",
                "title": "Manual generic prompt",
                "summary": "Generic item creation must not be a human backdoor.",
                "content": "Review this diff: {{diff}}",
                "created_by_name": "alex",
                "created_by_type": "USER",
                "source_type": "USER_CREATED",
                "status": "DRAFT",
            },
        ),
        (
            "knowledge_service",
            "/library/knowledge",
            {
                "title": "Manual knowledge",
                "summary": "Manual knowledge registration smoke.",
                "content": "Humans should not directly register library knowledge.",
                "body": "Humans can view, search, delete, and archive later.",
                "references": ["README.md"],
                "related_items": [],
                "created_by_name": "alex",
                "status": "DRAFT",
            },
        ),
        (
            "skill_service",
            "/library/skills",
            {
                "title": "Manual FastAPI skill",
                "summary": "Manual skill registration smoke.",
                "content": "Use narrow dependency overrides.",
                "purpose": "Register a reusable skill from the library UI.",
                "created_by_name": "alex",
                "status": "DRAFT",
            },
        ),
        (
            "prompt_service",
            "/library/prompts",
            {
                "title": "FastAPI review prompt",
                "summary": "Review backend API changes.",
                "content": "Review this diff: {{diff}}",
                "created_by_name": "review-agent",
                "created_by_type": "AGENT",
                "source_type": "AGENT_SUBMITTED",
                "status": "DRAFT",
            },
        ),
    ],
)
def test_manual_library_authoring_routes_are_not_exposed(
    provider_name: str,
    path: str,
    payload: dict[str, object],
) -> None:
    """Human library item, skill, prompt, and knowledge creation routes are absent."""
    with (
        override_library_provider(provider_name, FailingAuthoringService()),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post(path, json=payload)

    assert response.status_code in {404, 405}
