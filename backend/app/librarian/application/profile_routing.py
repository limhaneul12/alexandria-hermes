"""Deterministic librarian profile routing for Hermes collaboration."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from app.librarian.domain.contracts.hermes_collaboration_contracts import (
    HermesLibrarianAskCommand,
)
from app.librarian.domain.entities.read_models import AgentProfile
from app.librarian.domain.event_enum.collaboration_enums import (
    ArchiveRoutingToken,
    LibrarianProfileRole,
    QualityReviewRoutingToken,
)
from app.librarian.domain.repositories.agent_repository import IAgentRepository
from app.shared.exceptions import LibrarianResourceNotFoundError

_TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]*")
_DEFAULT_MAX_AUTO_PROFILES = 2


@dataclass(frozen=True, slots=True)
class LibrarianRoutingDecision:
    """Deterministic profile-routing result for one ask request."""

    selected_profiles: tuple[AgentProfile, ...]
    matched_specialties: tuple[str, ...]
    quality_review_added: bool
    reason: str
    max_librarian_agents: int | None


@dataclass(frozen=True, slots=True)
class ProfileScore:
    """Comparable profile score for deterministic routing."""

    profile: AgentProfile
    matched_specialties: tuple[str, ...]
    score: int


class LibrarianProfileRouter:
    """Select librarian profiles from prompt text and explicit request hints."""

    def __init__(self, agent_repo: IAgentRepository) -> None:
        """Initialize router dependencies.

        Args:
            agent_repo: Agent profile repository.
        """
        self.agent_repo = agent_repo

    async def route(
        self,
        command: HermesLibrarianAskCommand,
    ) -> LibrarianRoutingDecision:
        """Select librarian profiles by explicit id or specialty routing.

        Args:
            command: Ask-librarian command from API/MCP/CLI.

        Returns:
            LibrarianRoutingDecision: Selected profiles and routing evidence.
        """
        if command.librarian_profile_id is not None:
            return await self._route_requested_profile(command)

        profiles = [
            profile
            for profile in await self.agent_repo.list_all()
            if profile.librarian_enabled
        ]
        if not profiles:
            return LibrarianRoutingDecision(
                selected_profiles=(),
                matched_specialties=(),
                quality_review_added=False,
                reason="No librarian profiles configured",
                max_librarian_agents=command.max_librarian_agents,
            )

        max_agents = command.max_librarian_agents or _DEFAULT_MAX_AUTO_PROFILES
        return _route_scored_profiles(profiles, command, max_agents)

    async def _route_requested_profile(
        self,
        command: HermesLibrarianAskCommand,
    ) -> LibrarianRoutingDecision:
        profile = await self.agent_repo.get(command.librarian_profile_id or "")
        if profile is None:
            raise LibrarianResourceNotFoundError(
                f"Librarian profile not found: {command.librarian_profile_id}"
            )
        max_agents = command.max_librarian_agents or profile.max_librarian_agents
        matched = matched_specialties_for_profile(profile, command)
        return LibrarianRoutingDecision(
            selected_profiles=(profile,),
            matched_specialties=matched,
            quality_review_added=profile_role(profile)
            is LibrarianProfileRole.QUALITY_REVIEWER,
            reason=f"Requested librarian profile {profile.id}",
            max_librarian_agents=max_agents,
        )


def matched_specialties_for_profile(
    profile: AgentProfile,
    command: HermesLibrarianAskCommand,
) -> tuple[str, ...]:
    """Return specialties from a profile that match an ask request.

    Args:
        profile: Candidate librarian profile.
        command: Ask request with prompt and optional routing specialties.

    Returns:
        tuple[str, ...]: Normalized specialties that matched the request.
    """
    tokens = _query_tokens(command)
    matches: list[str] = []
    for specialty in _profile_specialties(profile):
        normalized = _normalize_token(specialty)
        if normalized in tokens:
            matches.append(specialty)
    return tuple(matches)


def profile_role(profile: AgentProfile) -> LibrarianProfileRole:
    """Parse persisted profile role with a safe default.

    Args:
        profile: Librarian profile read model.

    Returns:
        LibrarianProfileRole: Parsed role, defaulting to DEFAULT_SEARCH.
    """
    try:
        return LibrarianProfileRole(profile.librarian_role)
    except ValueError:
        return LibrarianProfileRole.DEFAULT_SEARCH


def _route_scored_profiles(
    profiles: list[AgentProfile],
    command: HermesLibrarianAskCommand,
    max_agents: int,
) -> LibrarianRoutingDecision:
    scored = _scored_profiles(profiles, command)
    selected: list[AgentProfile] = []
    matched_specialties: list[str] = []
    quality_review_added = False
    for score in scored:
        if len(selected) >= max_agents:
            break
        role = profile_role(score.profile)
        if role is LibrarianProfileRole.ARCHIVIST_CURATOR and not _archive_requested(
            command
        ):
            continue
        if (
            role is LibrarianProfileRole.QUALITY_REVIEWER
            and not _quality_review_requested(command)
        ):
            continue
        if role is LibrarianProfileRole.SPECIALIST and not score.matched_specialties:
            continue
        selected.append(score.profile)
        matched_specialties.extend(score.matched_specialties)
        if role is LibrarianProfileRole.QUALITY_REVIEWER:
            quality_review_added = True

    if not selected:
        default_profile = _first_default_profile(profiles)
        if default_profile is not None:
            selected.append(default_profile)

    unique_matches = tuple(dict.fromkeys(matched_specialties))
    reason = _routing_reason(selected, unique_matches, quality_review_added)
    return LibrarianRoutingDecision(
        selected_profiles=tuple(selected),
        matched_specialties=unique_matches,
        quality_review_added=quality_review_added,
        reason=reason,
        max_librarian_agents=max_agents,
    )


def _scored_profiles(
    profiles: list[AgentProfile],
    command: HermesLibrarianAskCommand,
) -> list[ProfileScore]:
    scores = [_score_profile(profile, command) for profile in profiles]
    return sorted(
        scores,
        key=lambda item: (
            -item.score,
            item.profile.librarian_routing_priority,
            item.profile.name,
        ),
    )


def _score_profile(
    profile: AgentProfile, command: HermesLibrarianAskCommand
) -> ProfileScore:
    matches = matched_specialties_for_profile(profile, command)
    role = profile_role(profile)
    role_bonus = 0
    if role is LibrarianProfileRole.DEFAULT_SEARCH:
        role_bonus = 3
    if role is LibrarianProfileRole.SPECIALIST and matches:
        role_bonus = 20
    if role is LibrarianProfileRole.QUALITY_REVIEWER and _quality_review_requested(
        command
    ):
        role_bonus = 15
    if role is LibrarianProfileRole.ARCHIVIST_CURATOR and _archive_requested(command):
        role_bonus = 12
    score = (len(matches) * 10) + role_bonus - profile.librarian_routing_priority
    return ProfileScore(profile=profile, matched_specialties=matches, score=score)


def _query_tokens(command: HermesLibrarianAskCommand) -> set[str]:
    raw = " ".join(
        part
        for part in (command.prompt, command.task_summary, command.project)
        if part is not None
    )
    tokens = {_normalize_token(token) for token in _TOKEN_PATTERN.findall(raw.lower())}
    tokens.update(
        _normalize_token(specialty) for specialty in command.routing_specialties
    )
    return {token for token in tokens if token}


def _normalize_token(value: str) -> str:
    return value.strip().lower().replace(" ", "-")


def _profile_specialties(profile: AgentProfile) -> list[str]:
    if profile.librarian_specialties:
        return [_normalize_token(item) for item in profile.librarian_specialties]
    return [_normalize_token(item) for item in profile.capabilities]


def _quality_review_requested(command: HermesLibrarianAskCommand) -> bool:
    return _has_routing_token(_query_tokens(command), QualityReviewRoutingToken)


def _archive_requested(command: HermesLibrarianAskCommand) -> bool:
    return _has_routing_token(_query_tokens(command), ArchiveRoutingToken)


def _has_routing_token(tokens: set[str], routing_tokens: type[StrEnum]) -> bool:
    """Return whether normalized prompt tokens include any routing enum value.

    Args:
        tokens: Normalized prompt/project/task tokens.
        routing_tokens: Routing token enum class to match.

    Returns:
        bool: ``True`` when at least one routing enum value is present.
    """
    return any(routing_token.value in tokens for routing_token in routing_tokens)


def _first_default_profile(profiles: list[AgentProfile]) -> AgentProfile | None:
    defaults = [
        profile
        for profile in profiles
        if profile_role(profile) is LibrarianProfileRole.DEFAULT_SEARCH
    ]
    if defaults:
        return sorted(
            defaults, key=lambda item: (item.librarian_routing_priority, item.name)
        )[0]
    if profiles:
        return sorted(
            profiles, key=lambda item: (item.librarian_routing_priority, item.name)
        )[0]
    return None


def _routing_reason(
    selected: list[AgentProfile],
    matched_specialties: tuple[str, ...],
    quality_review_added: bool,
) -> str:
    if not selected:
        return "No librarian profiles configured"
    if matched_specialties and quality_review_added:
        return "Matched specialties and added quality reviewer for risk tokens"
    if matched_specialties:
        return "Matched prompt tokens against specialist specialties"
    if quality_review_added:
        return "Added quality reviewer for risk tokens"
    return "Selected default librarian search profile"
