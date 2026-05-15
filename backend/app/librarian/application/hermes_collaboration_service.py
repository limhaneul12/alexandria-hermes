"""Hermes-facing collaboration service for librarian fallback decisions."""

from __future__ import annotations

import asyncio
import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from app.connections.domain.entities.read_models import LibrarianProvider
from app.connections.domain.repositories.librarian_repository import (
    ILibrarianProviderRepository,
    IProviderSecretRepository,
)
from app.librarian.application.provider_execution_policy import (
    provider_can_execute,
)
from app.librarian.domain.contracts.hermes_collaboration_contracts import (
    HermesLibrarianAskCommand,
    HermesLibrarianAskResult,
    LibrarianDelegateResult,
    LibrarianJobStatusResult,
)
from app.librarian.domain.entities.read_models import AgentProfile
from app.librarian.domain.event_enum.collaboration_enums import (
    AcquisitionDecision,
    LibrarianDelegateKind,
    LibrarianDelegateStatus,
    LibrarianDelegationStatus,
    LibrarianProfileRole,
)
from app.librarian.domain.repositories.agent_repository import IAgentRepository
from app.librarian.domain.types.hermes_collaboration_payload_types import (
    HermesLibrarianAskPayload,
    LibrarianDelegatePayload,
    LibrarianJobStatusPayload,
)
from app.shared.exceptions import NotFoundError
from app.shared.types.types_convert_utils import now_utc

_JOB_PREFIX = "librarian-job-"
_SELF_RESEARCH_RECOMMENDATION = (
    "적절한 skill이 없다면 Hermes가 먼저 공식 문서나 웹 근거를 조사해 "
    "skill candidate를 제출할 수 있습니다. 바쁘면 사서에게 위임하세요."
)
_DELEGATION_COMPLETED_MESSAGE = (
    "사서 delegate가 완료되었습니다. delegates 응답에서 profile별 결과와 "
    "matched_specialties를 확인하세요."
)
_QUALITY_REVIEW_TOKENS = frozenset(
    {
        "security",
        "oauth",
        "auth",
        "token",
        "secret",
        "production",
        "deploy",
        "risk",
        "dangerous",
        "review",
        "validate",
        "verify",
        "candidate",
        "prompt",
    }
)
_ARCHIVE_TOKENS = frozenset({"archive", "curate", "stale", "duplicate", "hygiene"})
_TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]*")
_DEFAULT_MAX_AUTO_PROFILES = 2


@dataclass(frozen=True, slots=True)
class LibrarianProfileResolution:
    """Resolved librarian execution settings for one Hermes request."""

    provider_id: str | None
    librarian_profile_id: str | None
    librarian_model: str | None
    librarian_role_prompt: str | None
    max_librarian_agents: int | None


@dataclass(frozen=True, slots=True)
class LibrarianRoutingDecision:
    """Deterministic profile-routing result for one ask request."""

    selected_profiles: tuple[AgentProfile, ...]
    matched_specialties: tuple[str, ...]
    quality_review_added: bool
    reason: str
    max_librarian_agents: int | None


@dataclass(frozen=True, slots=True)
class LibrarianExecutionPlan:
    """One profile/provider pair that can participate in a response."""

    profile: AgentProfile | None
    provider: LibrarianProvider | None
    resolution: LibrarianProfileResolution
    matched_specialties: tuple[str, ...]


class HermesCollaborationService:
    """Coordinate Hermes self-acquisition and librarian delegation decisions."""

    def __init__(
        self,
        provider_repo: ILibrarianProviderRepository,
        agent_repo: IAgentRepository,
        secret_repo: IProviderSecretRepository,
        now_provider: Callable[[], datetime] = now_utc,
    ) -> None:
        """Initialize collaboration service dependencies.

        Args:
            provider_repo: Librarian provider repository.
            agent_repo: Agent profile repository.
            secret_repo: Provider secret repository used for execution readiness.
            now_provider: Clock boundary for deterministic job ids.
        """
        self.provider_repo = provider_repo
        self.agent_repo = agent_repo
        self.secret_repo = secret_repo
        self.now_provider = now_provider

    async def ask_librarian(
        self,
        command: HermesLibrarianAskCommand,
    ) -> HermesLibrarianAskPayload:
        """Return collaboration guidance or a profile-backed delegation result.

        Args:
            command: Ask-librarian command from API/MCP/CLI.

        Returns:
            HermesLibrarianAskPayload: Public collaboration result.
        """
        routing = await self._route_profiles(command)
        providers = await self.provider_repo.list_all()
        executable_providers = await self._execution_ready_providers(providers)
        plans = self._execution_plans(command, routing, executable_providers)
        executable_plans = [plan for plan in plans if plan.provider is not None]
        representative_plan = (
            executable_plans[0] if executable_plans else _first_plan(plans)
        )
        representative_resolution = _representative_resolution(
            command,
            routing,
            representative_plan,
        )
        should_delegate = command.delegate_to_librarian and bool(executable_plans)
        job_id = self._job_id(
            command, representative_resolution, routing, should_delegate
        )
        delegates: list[LibrarianDelegateResult] = []
        status = LibrarianDelegationStatus.GUIDANCE_ONLY
        decision = AcquisitionDecision.SUGGEST_HERMES_RESEARCH
        recommendation = _SELF_RESEARCH_RECOMMENDATION
        if should_delegate:
            delegates = await _execute_delegates(
                executable_plans, routing.max_librarian_agents
            )
            if delegates:
                status = LibrarianDelegationStatus.COMPLETED
                decision = AcquisitionDecision.DELEGATE_TO_LIBRARIAN
                recommendation = _DELEGATION_COMPLETED_MESSAGE

        route_preview = _route_preview(
            representative_plan=representative_plan,
            routing=routing,
            delegated=should_delegate,
            executable_count=len(executable_plans),
        )
        result = HermesLibrarianAskResult(
            job_id=job_id,
            status=status,
            decision=decision,
            librarian_available=bool(executable_plans),
            self_acquisition_allowed=True,
            recommendation=recommendation,
            provider_id=_provider_id(representative_plan),
            candidate_id=None,
            librarian_profile_id=_profile_id(representative_plan),
            librarian_model=representative_resolution.librarian_model,
            librarian_role_prompt=representative_resolution.librarian_role_prompt,
            max_librarian_agents=representative_resolution.max_librarian_agents,
            route_preview=route_preview,
            selected_profiles=[profile.id for profile in routing.selected_profiles],
            matched_specialties=list(routing.matched_specialties),
            quality_review_added=routing.quality_review_added,
            routing_reason=routing.reason,
            delegates=delegates,
        )
        return _ask_payload(result)

    async def _route_profiles(
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
            profile = await self.agent_repo.get(command.librarian_profile_id)
            if profile is None:
                raise NotFoundError(
                    f"Librarian profile not found: {command.librarian_profile_id}"
                )
            max_agents = command.max_librarian_agents or profile.max_librarian_agents
            matched = _matched_specialties(profile, command)
            return LibrarianRoutingDecision(
                selected_profiles=(profile,),
                matched_specialties=tuple(matched),
                quality_review_added=_profile_role(profile)
                is LibrarianProfileRole.QUALITY_REVIEWER,
                reason=f"Requested librarian profile {profile.id}",
                max_librarian_agents=max_agents,
            )

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
        scored = _scored_profiles(profiles, command)
        selected: list[AgentProfile] = []
        matched_specialties: list[str] = []
        quality_review_added = False
        for score in scored:
            if len(selected) >= max_agents:
                break
            role = _profile_role(score.profile)
            if (
                role is LibrarianProfileRole.ARCHIVIST_CURATOR
                and not _archive_requested(command)
            ):
                continue
            if (
                role is LibrarianProfileRole.QUALITY_REVIEWER
                and not _quality_review_requested(command)
            ):
                continue
            if (
                role is LibrarianProfileRole.SPECIALIST
                and not score.matched_specialties
            ):
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

    async def job_status(self, job_id: str) -> LibrarianJobStatusPayload:
        """Return non-durable job status for an ask-librarian request id.

        Args:
            job_id: Job id returned by ask-librarian.

        Returns:
            LibrarianJobStatusPayload: Public job status.
        """
        if not job_id.startswith(_JOB_PREFIX):
            raise NotFoundError(f"Librarian job not found: {job_id}")
        result = LibrarianJobStatusResult(
            job_id=job_id,
            status=LibrarianDelegationStatus.GUIDANCE_ONLY,
            result_available=False,
            message=(
                "No durable librarian job is queued; ask responses use "
                "synchronous delegates and return results inline."
            ),
        )
        return _job_status_payload(result)

    async def _execution_ready_providers(
        self,
        providers: list[LibrarianProvider],
    ) -> list[LibrarianProvider]:
        execution_ready_providers: list[LibrarianProvider] = []
        for provider in providers:
            can_execute = await provider_can_execute(
                provider,
                self.secret_repo,
                self.now_provider,
            )
            if can_execute:
                execution_ready_providers.append(provider)
        return execution_ready_providers

    def _execution_plans(
        self,
        command: HermesLibrarianAskCommand,
        routing: LibrarianRoutingDecision,
        executable_providers: list[LibrarianProvider],
    ) -> list[LibrarianExecutionPlan]:
        provider_by_id = {provider.id: provider for provider in executable_providers}
        plans: list[LibrarianExecutionPlan] = []
        for profile in routing.selected_profiles:
            resolution = _profile_resolution(
                command, profile, routing.max_librarian_agents
            )
            provider = _plan_provider(
                resolution.provider_id, provider_by_id, executable_providers
            )
            plans.append(
                LibrarianExecutionPlan(
                    profile=profile,
                    provider=provider,
                    resolution=resolution,
                    matched_specialties=tuple(_matched_specialties(profile, command)),
                )
            )
        if plans:
            return plans
        provider = _plan_provider(
            command.provider_id, provider_by_id, executable_providers
        )
        if provider is None and not command.provider_id and executable_providers:
            provider = executable_providers[0]
        resolution = LibrarianProfileResolution(
            provider_id=command.provider_id,
            librarian_profile_id=None,
            librarian_model=command.librarian_model,
            librarian_role_prompt=command.librarian_role_prompt,
            max_librarian_agents=command.max_librarian_agents,
        )
        return [
            LibrarianExecutionPlan(
                profile=None,
                provider=provider,
                resolution=resolution,
                matched_specialties=(),
            )
        ]

    def _job_id(
        self,
        command: HermesLibrarianAskCommand,
        resolution: LibrarianProfileResolution,
        routing: LibrarianRoutingDecision,
        delegated: bool,
    ) -> str:
        timestamp = self.now_provider().isoformat()
        digest = hashlib.sha256(
            (
                f"{command.agent_name}:{command.prompt}:{command.project}:"
                f"{command.task_summary}:{resolution.provider_id}:"
                f"{resolution.librarian_profile_id}:{resolution.librarian_model}:"
                f"{resolution.max_librarian_agents}:{routing.selected_profiles}:"
                f"{routing.matched_specialties}:{delegated}:{timestamp}"
            ).encode()
        ).hexdigest()[:12]
        return f"{_JOB_PREFIX}{digest}"


@dataclass(frozen=True, slots=True)
class ProfileScore:
    """Comparable profile score for deterministic routing."""

    profile: AgentProfile
    matched_specialties: tuple[str, ...]
    score: int


def _profile_resolution(
    command: HermesLibrarianAskCommand,
    profile: AgentProfile,
    max_librarian_agents: int | None,
) -> LibrarianProfileResolution:
    provider_id = command.provider_id
    if provider_id is None:
        provider_id = profile.preferred_librarian_provider
    librarian_model = command.librarian_model
    if librarian_model is None:
        librarian_model = profile.preferred_librarian_model
    librarian_role_prompt = command.librarian_role_prompt
    if librarian_role_prompt is None:
        librarian_role_prompt = profile.librarian_role_prompt
    return LibrarianProfileResolution(
        provider_id=provider_id,
        librarian_profile_id=profile.id,
        librarian_model=librarian_model,
        librarian_role_prompt=librarian_role_prompt,
        max_librarian_agents=max_librarian_agents or profile.max_librarian_agents,
    )


def _ask_payload(result: HermesLibrarianAskResult) -> HermesLibrarianAskPayload:
    delegates = [_delegate_payload(delegate) for delegate in result.delegates]
    return HermesLibrarianAskPayload(
        job_id=result.job_id,
        status=result.status,
        decision=result.decision,
        librarian_available=result.librarian_available,
        self_acquisition_allowed=result.self_acquisition_allowed,
        recommendation=result.recommendation,
        provider_id=result.provider_id,
        candidate_id=result.candidate_id,
        librarian_profile_id=result.librarian_profile_id,
        librarian_model=result.librarian_model,
        librarian_role_prompt=result.librarian_role_prompt,
        max_librarian_agents=result.max_librarian_agents,
        route_preview=result.route_preview,
        selected_profiles=result.selected_profiles,
        matched_specialties=result.matched_specialties,
        quality_review_added=result.quality_review_added,
        routing_reason=result.routing_reason,
        delegates=delegates,
    )


def _delegate_payload(result: LibrarianDelegateResult) -> LibrarianDelegatePayload:
    payload = LibrarianDelegatePayload(
        profile_id=result.profile_id,
        provider_id=result.provider_id,
        status=result.status,
        delegate_type=result.delegate_type,
        summary=result.summary,
        matched_specialties=result.matched_specialties,
    )
    return payload


def _job_status_payload(
    result: LibrarianJobStatusResult,
) -> LibrarianJobStatusPayload:
    return LibrarianJobStatusPayload(
        job_id=result.job_id,
        status=result.status,
        result_available=result.result_available,
        message=result.message,
    )


def _route_preview(
    representative_plan: LibrarianExecutionPlan | None,
    routing: LibrarianRoutingDecision,
    delegated: bool,
    executable_count: int,
) -> list[str]:
    preview = ["Hermes direct search first"]
    if not routing.selected_profiles:
        preview.append("No librarian profiles configured")
    else:
        selected = ", ".join(profile.id for profile in routing.selected_profiles)
        preview.append(f"Selected profiles: {selected}")
    if routing.matched_specialties:
        preview.append(f"Matched specialties: {', '.join(routing.matched_specialties)}")
    preview.append(f"Routing reason: {routing.reason}")
    if representative_plan is None or representative_plan.provider is None:
        preview.append("No executable librarian provider available")
        preview.append("Hermes self-acquisition path")
        return preview
    preview.append(f"Specialized librarian provider: {representative_plan.provider.id}")
    if delegated:
        preview.append(f"Completed delegated librarians: {executable_count}")
    else:
        preview.append("Preview only; no librarian delegation queued")
    return preview


async def _execute_delegates(
    plans: list[LibrarianExecutionPlan],
    max_librarian_agents: int | None,
) -> list[LibrarianDelegateResult]:
    limit = max_librarian_agents or 1
    semaphore = asyncio.Semaphore(limit)

    async def execute_one(plan: LibrarianExecutionPlan) -> LibrarianDelegateResult:
        async with semaphore:
            return _delegate_result(plan)

    selected_plans = plans[:limit]
    return list(await asyncio.gather(*(execute_one(plan) for plan in selected_plans)))


def _delegate_result(plan: LibrarianExecutionPlan) -> LibrarianDelegateResult:
    profile_id = "request-default" if plan.profile is None else plan.profile.id
    role = LibrarianProfileRole.DEFAULT_SEARCH
    if plan.profile is not None:
        role = _profile_role(plan.profile)
    delegate_type = _delegate_kind(role)
    summary = _delegate_summary(role, plan.matched_specialties)
    provider_id = None if plan.provider is None else plan.provider.id
    return LibrarianDelegateResult(
        profile_id=profile_id,
        provider_id=provider_id,
        status=LibrarianDelegateStatus.COMPLETED,
        delegate_type=delegate_type,
        summary=summary,
        matched_specialties=list(plan.matched_specialties),
    )


def _delegate_kind(role: LibrarianProfileRole) -> LibrarianDelegateKind:
    if role is LibrarianProfileRole.SPECIALIST:
        return LibrarianDelegateKind.SPECIALTY_REVIEW
    if role is LibrarianProfileRole.QUALITY_REVIEWER:
        return LibrarianDelegateKind.QUALITY_REVIEW
    if role is LibrarianProfileRole.ARCHIVIST_CURATOR:
        return LibrarianDelegateKind.ARCHIVE_CURATION
    return LibrarianDelegateKind.LIBRARY_SEARCH


def _delegate_summary(
    role: LibrarianProfileRole,
    matched_specialties: tuple[str, ...],
) -> str:
    if role is LibrarianProfileRole.SPECIALIST and matched_specialties:
        return f"Specialist reviewed matching specialties: {', '.join(matched_specialties)}"
    if role is LibrarianProfileRole.QUALITY_REVIEWER:
        return "Quality reviewer checked risk, evidence, and duplication concerns."
    if role is LibrarianProfileRole.ARCHIVIST_CURATOR:
        return "Archivist curator checked stale context and archive hygiene."
    return "Default search librarian checked reusable library/search routes."


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
    matches = tuple(_matched_specialties(profile, command))
    role = _profile_role(profile)
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


def _matched_specialties(
    profile: AgentProfile,
    command: HermesLibrarianAskCommand,
) -> list[str]:
    tokens = _query_tokens(command)
    matches: list[str] = []
    for specialty in _profile_specialties(profile):
        normalized = _normalize_token(specialty)
        if normalized in tokens:
            matches.append(specialty)
    return matches


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


def _profile_role(profile: AgentProfile) -> LibrarianProfileRole:
    try:
        return LibrarianProfileRole(profile.librarian_role)
    except ValueError:
        return LibrarianProfileRole.DEFAULT_SEARCH


def _quality_review_requested(command: HermesLibrarianAskCommand) -> bool:
    return bool(_query_tokens(command) & _QUALITY_REVIEW_TOKENS)


def _archive_requested(command: HermesLibrarianAskCommand) -> bool:
    return bool(_query_tokens(command) & _ARCHIVE_TOKENS)


def _first_default_profile(profiles: list[AgentProfile]) -> AgentProfile | None:
    defaults = [
        profile
        for profile in profiles
        if _profile_role(profile) is LibrarianProfileRole.DEFAULT_SEARCH
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


def _plan_provider(
    provider_id: str | None,
    provider_by_id: dict[str, LibrarianProvider],
    executable_providers: list[LibrarianProvider],
) -> LibrarianProvider | None:
    if provider_id is not None:
        return provider_by_id.get(provider_id)
    if executable_providers:
        return executable_providers[0]
    return None


def _first_plan(plans: list[LibrarianExecutionPlan]) -> LibrarianExecutionPlan | None:
    if plans:
        return plans[0]
    return None


def _representative_resolution(
    command: HermesLibrarianAskCommand,
    routing: LibrarianRoutingDecision,
    representative_plan: LibrarianExecutionPlan | None,
) -> LibrarianProfileResolution:
    if representative_plan is not None:
        return representative_plan.resolution
    return LibrarianProfileResolution(
        provider_id=command.provider_id,
        librarian_profile_id=None,
        librarian_model=command.librarian_model,
        librarian_role_prompt=command.librarian_role_prompt,
        max_librarian_agents=routing.max_librarian_agents,
    )


def _provider_id(plan: LibrarianExecutionPlan | None) -> str | None:
    if plan is None or plan.provider is None:
        return None
    return plan.provider.id


def _profile_id(plan: LibrarianExecutionPlan | None) -> str | None:
    if plan is None or plan.profile is None:
        return None
    return plan.profile.id
