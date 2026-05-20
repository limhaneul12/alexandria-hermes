"""Collaboration CLI payload helper tests."""

from __future__ import annotations

from app.cli_support.contracts.librarian_command_contracts import (
    LibrarianAskCommand,
    LibrarianProfileUpdateCommand,
    LibrarianRoutePreviewCommand,
    UsageRecordCliCommand,
)
from app.cli_support.handlers.collaboration_helpers import (
    librarian_ask_body,
    librarian_route_body,
    profile_update_body,
    usage_record_body,
)
from app.library.domain.event_enum.usage_enums import SelectionSource


def test_usage_record_body_uses_structured_feedback_when_context_exists() -> None:
    """Usage body creation should omit empty fields and shape contextual feedback."""
    body = usage_record_body(
        UsageRecordCliCommand(
            item_id="skill-1",
            item_type="SKILL",
            selection_source=SelectionSource.SEARCH,
            agent_name="codex",
            success=True,
            query=None,
            librarian_provider=None,
            project="alexandria",
            task_summary="OAuth review",
            feedback="Useful.",
        )
    )

    assert body == {
        "item_id": "skill-1",
        "item_type": "SKILL",
        "agent_name": "codex",
        "selection_source": "SEARCH",
        "success": True,
        "feedback": {
            "project": "alexandria",
            "task_summary": "OAuth review",
            "comment": "Useful.",
        },
    }


def test_librarian_ask_body_omits_empty_optional_values() -> None:
    """Ask-librarian body creation should use schema omission for empty optionals."""
    body = librarian_ask_body(
        LibrarianAskCommand(
            prompt="Review OAuth",
            delegate_to_librarian=True,
            provider_id=None,
            agent_name="Hermes",
            project=None,
            task_summary=None,
            librarian_profile_id=None,
            librarian_model=None,
            librarian_role_prompt=None,
            max_librarian_agents=None,
            routing_specialties=[],
        )
    )

    assert body == {
        "prompt": "Review OAuth",
        "agent_name": "Hermes",
        "delegate_to_librarian": True,
    }


def test_librarian_route_body_forces_preview_without_delegation() -> None:
    """Route-preview body creation should force delegate_to_librarian false."""
    body = librarian_route_body(
        LibrarianRoutePreviewCommand(
            prompt="Review OAuth",
            provider_id="provider-1",
            agent_name="Hermes",
            project="alexandria",
            task_summary=None,
            librarian_profile_id=None,
            librarian_model="gpt-5.5",
            librarian_role_prompt=None,
            max_librarian_agents=2,
            routing_specialties=["oauth"],
        )
    )

    assert body == {
        "prompt": "Review OAuth",
        "agent_name": "Hermes",
        "delegate_to_librarian": False,
        "provider_id": "provider-1",
        "librarian_model": "gpt-5.5",
        "max_librarian_agents": 2,
        "routing_specialties": ["oauth"],
        "project": "alexandria",
    }


def test_profile_update_body_preserves_specialty_updates() -> None:
    """Profile patch body creation should include computed specialty changes."""
    body = profile_update_body(
        LibrarianProfileUpdateCommand(
            profile_id="profile-1",
            name=None,
            role="QUALITY_REVIEWER",
            add_specialties=["security"],
            remove_specialties=["old"],
            provider_id=None,
            model="gpt-5.5",
            delegate_limit=None,
            role_prompt="Review risky changes.",
            role_prompt_file=None,
            routing_priority=5,
            enabled=None,
        ),
        current={"librarian_specialties": ["old", "oauth"]},
    )

    assert body == {
        "librarian_role": "QUALITY_REVIEWER",
        "preferred_librarian_model": "gpt-5.5",
        "librarian_routing_priority": 5,
        "description": "Review risky changes.",
        "librarian_role_prompt": "Review risky changes.",
        "capabilities": ["oauth", "security"],
        "librarian_specialties": ["oauth", "security"],
    }
