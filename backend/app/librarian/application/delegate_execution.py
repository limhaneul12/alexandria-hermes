"""Synchronous librarian delegate planning and execution helpers."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.connections.domain.entities.read_models import LibrarianProvider
from app.librarian.application.profile_routing import (
    LibrarianRoutingDecision,
    matched_specialties_for_profile,
    profile_role,
)
from app.librarian.domain.contracts.hermes_collaboration_contracts import (
    HermesLibrarianAskCommand,
    LibrarianDelegateResult,
)
from app.librarian.domain.entities.read_models import AgentProfile
from app.librarian.domain.event_enum.collaboration_enums import (
    LibrarianDelegateKind,
    LibrarianDelegateStatus,
    LibrarianProfileRole,
)


@dataclass(frozen=True, slots=True)
class LibrarianProfileResolution:
    """Resolved librarian execution settings for one Hermes request."""

    provider_id: str | None
    librarian_profile_id: str | None
    librarian_model: str | None
    librarian_role_prompt: str | None
    max_librarian_agents: int | None


@dataclass(frozen=True, slots=True)
class LibrarianExecutionPlan:
    """One profile/provider pair that can participate in a response."""

    profile: AgentProfile | None
    provider: LibrarianProvider | None
    resolution: LibrarianProfileResolution
    matched_specialties: tuple[str, ...]


class LibrarianDelegateExecutor(ABC):
    """Boundary for provider-backed delegate execution."""

    @abstractmethod
    async def execute(
        self,
        *,
        command: HermesLibrarianAskCommand,
        plan: LibrarianExecutionPlan,
        fallback: LibrarianDelegateResult,
    ) -> LibrarianDelegateResult:
        """Execute one delegate plan with an external provider.

        Args:
            command: Ask-librarian command that carries the prompt.
            plan: Resolved provider/profile execution plan.
            fallback: Safe deterministic delegate result for metadata and fallback.

        Returns:
            LibrarianDelegateResult: Provider-backed delegate result.
        """


def build_execution_plans(
    command: HermesLibrarianAskCommand,
    routing: LibrarianRoutingDecision,
    executable_providers: list[LibrarianProvider],
) -> list[LibrarianExecutionPlan]:
    """Build provider/profile execution plans for a collaboration request.

    Args:
        command: Ask-librarian command from API/MCP/CLI.
        routing: Selected librarian profiles and routing metadata.
        executable_providers: Providers that passed execution-readiness checks.

    Returns:
        list[LibrarianExecutionPlan]: Candidate delegate plans.
    """
    provider_by_id = {provider.id: provider for provider in executable_providers}
    plans: list[LibrarianExecutionPlan] = []
    for profile in routing.selected_profiles:
        resolution = _profile_resolution(command, profile, routing.max_librarian_agents)
        provider = _plan_provider(
            resolution.provider_id, provider_by_id, executable_providers
        )
        plans.append(
            LibrarianExecutionPlan(
                profile=profile,
                provider=provider,
                resolution=resolution,
                matched_specialties=matched_specialties_for_profile(profile, command),
            )
        )
    if plans:
        return plans
    return [_request_default_plan(command, provider_by_id, executable_providers)]


async def execute_delegates(
    plans: list[LibrarianExecutionPlan],
    max_librarian_agents: int | None,
    *,
    command: HermesLibrarianAskCommand | None = None,
    executor: LibrarianDelegateExecutor | None = None,
) -> list[LibrarianDelegateResult]:
    """Execute delegate plans synchronously with bounded parallelism.

    Args:
        plans: Executable delegate plans.
        max_librarian_agents: Maximum concurrent delegate count.
        command: Optional ask command required for provider-backed execution.
        executor: Optional provider execution boundary.

    Returns:
        list[LibrarianDelegateResult]: Inline delegate results.
    """
    limit = max_librarian_agents or 1
    semaphore = asyncio.Semaphore(limit)

    async def execute_one(plan: LibrarianExecutionPlan) -> LibrarianDelegateResult:
        async with semaphore:
            fallback = _delegate_result(plan)
            if executor is None or command is None:
                return fallback
            return await executor.execute(
                command=command,
                plan=plan,
                fallback=fallback,
            )

    selected_plans = plans[:limit]
    return list(await asyncio.gather(*(execute_one(plan) for plan in selected_plans)))


def build_route_preview(
    representative_plan: LibrarianExecutionPlan | None,
    routing: LibrarianRoutingDecision,
    delegated: bool,
    executable_count: int,
) -> list[str]:
    """Create human-readable routing evidence for the ask response.

    Args:
        representative_plan: Plan used for top-level provider/profile fields.
        routing: Selected profiles and matching evidence.
        delegated: Whether delegates were executed.
        executable_count: Number of executable plans.

    Returns:
        list[str]: Ordered route-preview messages.
    """
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
        if executable_count <= 0:
            preview.append("No delegated librarians completed")
            return preview
        preview.append(f"Completed delegated librarians: {executable_count}")
    else:
        preview.append("Preview only; no librarian delegation queued")
    return preview


def first_plan(plans: list[LibrarianExecutionPlan]) -> LibrarianExecutionPlan | None:
    """Return the first execution plan when one exists.

    Args:
        plans: Planned delegate executions.

    Returns:
        LibrarianExecutionPlan | None: First plan, or None.
    """
    if plans:
        return plans[0]
    return None


def representative_resolution(
    command: HermesLibrarianAskCommand,
    routing: LibrarianRoutingDecision,
    representative_plan: LibrarianExecutionPlan | None,
) -> LibrarianProfileResolution:
    """Resolve top-level response execution settings.

    Args:
        command: Ask-librarian command from API/MCP/CLI.
        routing: Selected profiles and routing metadata.
        representative_plan: Preferred executable or preview plan.

    Returns:
        LibrarianProfileResolution: Top-level execution settings.
    """
    if representative_plan is not None:
        return representative_plan.resolution
    return LibrarianProfileResolution(
        provider_id=command.provider_id,
        librarian_profile_id=None,
        librarian_model=command.librarian_model,
        librarian_role_prompt=command.librarian_role_prompt,
        max_librarian_agents=routing.max_librarian_agents,
    )


def execution_provider_id(plan: LibrarianExecutionPlan | None) -> str | None:
    """Return the provider id for a representative execution plan.

    Args:
        plan: Representative execution plan.

    Returns:
        str | None: Provider id when available.
    """
    if plan is None or plan.provider is None:
        return None
    return plan.provider.id


def execution_profile_id(plan: LibrarianExecutionPlan | None) -> str | None:
    """Return the profile id for a representative execution plan.

    Args:
        plan: Representative execution plan.

    Returns:
        str | None: Profile id when available.
    """
    if plan is None or plan.profile is None:
        return None
    return plan.profile.id


def _request_default_plan(
    command: HermesLibrarianAskCommand,
    provider_by_id: dict[str, LibrarianProvider],
    executable_providers: list[LibrarianProvider],
) -> LibrarianExecutionPlan:
    provider = _plan_provider(command.provider_id, provider_by_id, executable_providers)
    if provider is None and not command.provider_id and executable_providers:
        provider = executable_providers[0]
    resolution = LibrarianProfileResolution(
        provider_id=command.provider_id,
        librarian_profile_id=None,
        librarian_model=command.librarian_model,
        librarian_role_prompt=command.librarian_role_prompt,
        max_librarian_agents=command.max_librarian_agents,
    )
    return LibrarianExecutionPlan(
        profile=None,
        provider=provider,
        resolution=resolution,
        matched_specialties=(),
    )


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


def _delegate_result(plan: LibrarianExecutionPlan) -> LibrarianDelegateResult:
    profile_id = "request-default" if plan.profile is None else plan.profile.id
    role = LibrarianProfileRole.DEFAULT_SEARCH
    if plan.profile is not None:
        role = profile_role(plan.profile)
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
