"""Hermes-facing collaboration service for librarian fallback decisions."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import datetime

from app.connections.domain.entities.read_models import LibrarianProvider
from app.connections.domain.repositories.librarian_repository import (
    ILibrarianProviderRepository,
    IProviderSecretRepository,
)
from app.librarian.application.delegate_execution import (
    LibrarianDelegateExecutor,
    LibrarianExecutionPlan,
    LibrarianProfileResolution,
    build_execution_plans,
    build_route_preview,
    execute_delegates,
    execution_profile_id,
    execution_provider_id,
    first_plan,
    representative_resolution,
)
from app.librarian.application.profile_routing import (
    LibrarianProfileRouter,
    LibrarianRoutingDecision,
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
from app.librarian.domain.event_enum.collaboration_enums import (
    AcquisitionDecision,
    LibrarianDelegateStatus,
    LibrarianDelegationStatus,
)
from app.librarian.domain.repositories.agent_repository import IAgentRepository
from app.librarian.domain.types.hermes_collaboration_payload_types import (
    HermesLibrarianAskPayload,
    LibrarianDelegatePayload,
    LibrarianJobStatusPayload,
)
from app.shared.exceptions import LibrarianResourceNotFoundError
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
_DELEGATION_SKIPPED_MESSAGE = (
    "사서 delegate를 완료하지 못했습니다. delegates 응답의 SKIPPED 항목과 "
    "summary를 확인하고 Hermes 직접 조사 또는 인증/제공자 설정을 점검하세요."
)


class HermesCollaborationService:
    """Coordinate Hermes self-acquisition and librarian delegation decisions."""

    def __init__(
        self,
        provider_repo: ILibrarianProviderRepository,
        agent_repo: IAgentRepository,
        secret_repo: IProviderSecretRepository,
        now_provider: Callable[[], datetime] = now_utc,
        delegate_executor: LibrarianDelegateExecutor | None = None,
    ) -> None:
        """Initialize collaboration service dependencies.

        Args:
            provider_repo: Librarian provider repository.
            agent_repo: Agent profile repository.
            secret_repo: Provider secret repository used for execution readiness.
            now_provider: Clock boundary for deterministic job ids.
            delegate_executor: Optional provider-backed delegate executor.
        """
        self.provider_repo = provider_repo
        self.secret_repo = secret_repo
        self.now_provider = now_provider
        self.delegate_executor = delegate_executor
        self.profile_router = LibrarianProfileRouter(agent_repo)

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
        routing = await self.profile_router.route(command)
        providers = await self.provider_repo.list_all()
        executable_providers = await self._execution_ready_providers(providers)
        plans = build_execution_plans(command, routing, executable_providers)
        executable_plans = [plan for plan in plans if plan.provider is not None]
        representative_plan = (
            executable_plans[0] if executable_plans else first_plan(plans)
        )
        top_level_resolution = representative_resolution(
            command,
            routing,
            representative_plan,
        )
        should_delegate = command.delegate_to_librarian and bool(executable_plans)
        job_id = self._job_id(command, top_level_resolution, routing, should_delegate)
        delegates, status, decision, recommendation = await _delegate_decision(
            should_delegate,
            executable_plans,
            routing.max_librarian_agents,
            command=command,
            executor=self.delegate_executor,
        )
        route_preview = build_route_preview(
            representative_plan=representative_plan,
            routing=routing,
            delegated=should_delegate,
            executable_count=_completed_delegate_count(delegates),
        )
        result = HermesLibrarianAskResult(
            job_id=job_id,
            status=status,
            decision=decision,
            librarian_available=bool(executable_plans),
            self_acquisition_allowed=True,
            recommendation=recommendation,
            provider_id=execution_provider_id(representative_plan),
            candidate_id=None,
            librarian_profile_id=execution_profile_id(representative_plan),
            librarian_model=top_level_resolution.librarian_model,
            librarian_role_prompt=top_level_resolution.librarian_role_prompt,
            max_librarian_agents=top_level_resolution.max_librarian_agents,
            route_preview=route_preview,
            selected_profiles=[profile.id for profile in routing.selected_profiles],
            matched_specialties=list(routing.matched_specialties),
            quality_review_added=routing.quality_review_added,
            routing_reason=routing.reason,
            delegates=delegates,
        )
        return _ask_payload(result)

    async def job_status(self, job_id: str) -> LibrarianJobStatusPayload:
        """Return non-durable job status for an ask-librarian request id.

        Args:
            job_id: Job id returned by ask-librarian.

        Returns:
            LibrarianJobStatusPayload: Public job status.
        """
        if not job_id.startswith(_JOB_PREFIX):
            raise LibrarianResourceNotFoundError(f"Librarian job not found: {job_id}")
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


async def _delegate_decision(
    should_delegate: bool,
    executable_plans: list[LibrarianExecutionPlan],
    max_librarian_agents: int | None,
    *,
    command: HermesLibrarianAskCommand,
    executor: LibrarianDelegateExecutor | None,
) -> tuple[
    list[LibrarianDelegateResult], LibrarianDelegationStatus, AcquisitionDecision, str
]:
    delegates: list[LibrarianDelegateResult] = []
    status = LibrarianDelegationStatus.GUIDANCE_ONLY
    decision = AcquisitionDecision.SUGGEST_HERMES_RESEARCH
    recommendation = _SELF_RESEARCH_RECOMMENDATION
    if should_delegate:
        delegates = await execute_delegates(
            executable_plans,
            max_librarian_agents,
            command=command,
            executor=executor,
        )
        if _completed_delegate_count(delegates) > 0:
            status = LibrarianDelegationStatus.COMPLETED
            decision = AcquisitionDecision.DELEGATE_TO_LIBRARIAN
            recommendation = _DELEGATION_COMPLETED_MESSAGE
        elif delegates:
            recommendation = _DELEGATION_SKIPPED_MESSAGE
    return delegates, status, decision, recommendation


def _completed_delegate_count(delegates: list[LibrarianDelegateResult]) -> int:
    completed_count = sum(
        1
        for delegate in delegates
        if delegate.status is LibrarianDelegateStatus.COMPLETED
    )
    return completed_count


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
