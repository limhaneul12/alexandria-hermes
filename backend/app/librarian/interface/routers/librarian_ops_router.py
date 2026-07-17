"""Librarian collaboration and durable skill-acquisition routes."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from inspect import isawaitable
from typing import cast

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.container import ApplicationContainer
from app.librarian.application.hermes_collaboration_service import (
    HermesCollaborationService,
)
from app.librarian.application.knowledge_packet_compiler import KnowledgePacketCompiler
from app.librarian.application.skill_acquisition_runner import SkillAcquisitionRunner
from app.librarian.application.skill_acquisition_service import SkillAcquisitionService
from app.librarian.application.skill_artifact_publisher import (
    ObsidianSkillArtifactPublisher,
)
from app.librarian.application.skill_library_search_service import (
    SkillLibrarySearchService,
)
from app.librarian.domain.contracts.hermes_collaboration_contracts import (
    HermesLibrarianAskCommand,
)
from app.librarian.domain.event_enum.collaboration_enums import (
    SkillAcquisitionJobStatus,
)
from app.librarian.interface.schemas.librarian.hermes_collaboration_schemas import (
    AskLibrarianRequest,
    AskLibrarianResponse,
    LibrarianJobStatusResponse,
)
from app.librarian.interface.schemas.librarian.skill_acquisition_schemas import (
    SkillAcquisitionCompletionRequest,
    SkillAcquisitionJobRequest,
    SkillAcquisitionJobResponse,
    SkillCapabilitySearchRequest,
    SkillCapabilitySearchResponse,
    skill_acquisition_job_response,
    skill_capability_search_response,
)
from app.obsidian.application.obsidian_service import ObsidianService
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import LIBRARIAN_ROUTE_EXCEPTION_MAPPING
from app.shared.infrastructure.database import Database

router = APIRouter(
    prefix="/librarians",
    tags=["librarian"],
)
logger = logging.getLogger(__name__)


async def _run_skill_acquisition_background_job(
    *,
    database: Database,
    runner_factory: Callable[
        [], SkillAcquisitionRunner | Awaitable[SkillAcquisitionRunner]
    ],
    obsidian_service_factory: Callable[
        [], ObsidianService | Awaitable[ObsidianService]
    ],
    job_id: str,
) -> None:
    """Run one skill-acquisition job in an independently committed session.

    Args:
        database: Application database coordinator.
        runner_factory: Provider that builds a runner after the background
            session has been rebound.
        obsidian_service_factory: Provider that builds the Obsidian service after
            the background session has been rebound.
        job_id: Durable skill-acquisition job identifier.
    """
    async with database.request_session() as session:
        try:
            runner_candidate = runner_factory()
            if isawaitable(runner_candidate):
                runner = await cast(Awaitable[SkillAcquisitionRunner], runner_candidate)
            else:
                runner = runner_candidate
            obsidian_candidate = obsidian_service_factory()
            if isawaitable(obsidian_candidate):
                obsidian_service = await cast(
                    Awaitable[ObsidianService], obsidian_candidate
                )
            else:
                obsidian_service = obsidian_candidate
            await runner.run_job(
                job_id,
                artifact_publisher=ObsidianSkillArtifactPublisher(obsidian_service),
            )
        except Exception:
            # This is the background task transaction boundary. Roll back any
            # partially flushed state before FastAPI surfaces the task failure.
            await session.rollback()
            logger.exception(
                "Skill acquisition background task failed",
                extra={"job_id": job_id},
            )
            raise
        await session.commit()


def _ask_command(
    request: AskLibrarianRequest,
    compiler: KnowledgePacketCompiler,
) -> HermesLibrarianAskCommand:
    """Compile the request brief and build the application command.

    Args:
        request: Public ask-librarian request.
        compiler: Application service that compiles the delegate brief.

    Returns:
        HermesLibrarianAskCommand: Application command for collaboration routing.
    """
    brief = compiler.compile(
        prompt=request.prompt,
        project=request.project,
        budget_policy=request.budget.to_entity(),
        context_compact=None
        if request.context_compact is None
        else request.context_compact.to_entity(),
        source_refs=[source_ref.to_entity() for source_ref in request.source_refs],
    )
    command = request.to_command(
        librarian_brief=brief.packet_markdown,
        source_refs=brief.source_refs,
    )
    return command


@router.post(
    "/route-preview",
    response_model=AskLibrarianResponse,
    description="Preview librarian routing without queueing delegation.",
    status_code=status.HTTP_200_OK,
    summary="Preview librarian route",
)
@router_exception_status(LIBRARIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def route_preview(
    request: AskLibrarianRequest,
    collaboration_service: HermesCollaborationService = Depends(
        Provide[ApplicationContainer.librarian.hermes_collaboration_service]
    ),
    compiler: KnowledgePacketCompiler = Depends(
        Provide[ApplicationContainer.librarian.knowledge_packet_compiler]
    ),
) -> AskLibrarianResponse:
    """Preview the self-acquisition/librarian route for a Hermes prompt.

    Args:
        request: Ask-librarian request.
        collaboration_service: Collaboration service.
        compiler: Knowledge packet compiler dependency.

    Returns:
        AskLibrarianResponse: Guidance with route_preview populated.
    """
    command = _ask_command(
        request.model_copy(update={"delegate_to_librarian": False}),
        compiler,
    )
    payload = await collaboration_service.ask_librarian(command)
    validation = AskLibrarianResponse.model_validate(payload)
    return validation


@router.post(
    "/ask",
    response_model=AskLibrarianResponse,
    description="Librarian skill-acquisition operation.",
    status_code=status.HTTP_200_OK,
    summary="Ask librarian",
)
@router_exception_status(LIBRARIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def ask_librarian(
    request: AskLibrarianRequest,
    collaboration_service: HermesCollaborationService = Depends(
        Provide[ApplicationContainer.librarian.hermes_collaboration_service]
    ),
    compiler: KnowledgePacketCompiler = Depends(
        Provide[ApplicationContainer.librarian.knowledge_packet_compiler]
    ),
) -> AskLibrarianResponse:
    """Return Hermes self-acquisition or librarian delegation guidance.

    Args:
        request [AskLibrarianRequest]: Value supplied to ask_librarian.
        collaboration_service [HermesCollaborationService]: Value supplied to ask_librarian.
        compiler: Knowledge packet compiler dependency.

    Returns:
        AskLibrarianResponse: Value produced by ask_librarian.
    """
    payload = await collaboration_service.ask_librarian(_ask_command(request, compiler))
    validation = AskLibrarianResponse.model_validate(payload)
    return validation


@router.get(
    "/jobs/{job_id}",
    response_model=LibrarianJobStatusResponse,
    description="Librarian skill-acquisition operation.",
    status_code=status.HTTP_200_OK,
    summary="Librarian job status",
)
@router_exception_status(LIBRARIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def librarian_job_status(
    job_id: str,
    collaboration_service: HermesCollaborationService = Depends(
        Provide[ApplicationContainer.librarian.hermes_collaboration_service]
    ),
) -> LibrarianJobStatusResponse:
    """Return status for a guidance-only librarian request.

    Args:
        job_id [str]: Value supplied to librarian_job_status.
        collaboration_service [HermesCollaborationService]: Value supplied to librarian_job_status.

    Returns:
        LibrarianJobStatusResponse: Value produced by librarian_job_status.
    """
    payload = await collaboration_service.job_status(job_id)
    validation = LibrarianJobStatusResponse.model_validate(payload)
    return validation


@router.post(
    "/skill-library/search",
    response_model=SkillCapabilitySearchResponse,
    description="Search reusable skill notes and evaluate sufficiency before acquisition.",
    status_code=status.HTTP_200_OK,
    summary="Search skill library",
)
@router_exception_status(LIBRARIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def search_skill_library(
    request: SkillCapabilitySearchRequest,
    obsidian_service: ObsidianService = Depends(
        Provide[ApplicationContainer.obsidian.obsidian_service]
    ),
) -> SkillCapabilitySearchResponse:
    """Search existing skill artifacts before creating an acquisition job.

    Args:
        request: Normalized capability brief.
        obsidian_service: Obsidian-backed skill library search boundary.

    Returns:
        Sufficiency decision and normalized candidates.
    """
    result = await SkillLibrarySearchService(obsidian_service).search_first(
        request.to_brief()
    )
    return skill_capability_search_response(result)


@router.post(
    "/skill-acquisition-jobs",
    response_model=SkillAcquisitionJobResponse,
    description="Create a durable local skill-acquisition job.",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create skill acquisition job",
)
@router_exception_status(LIBRARIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def create_skill_acquisition_job(
    request: SkillAcquisitionJobRequest,
    background_tasks: BackgroundTasks,
    service: SkillAcquisitionService = Depends(
        Provide[ApplicationContainer.librarian.skill_acquisition_service]
    ),
    database: Database = Depends(Provide[ApplicationContainer.database]),
    runner_factory: Callable[
        [], SkillAcquisitionRunner | Awaitable[SkillAcquisitionRunner]
    ] = Depends(
        Provide[ApplicationContainer.librarian.skill_acquisition_runner.provider]
    ),
    obsidian_service_factory: Callable[
        [], ObsidianService | Awaitable[ObsidianService]
    ] = Depends(Provide[ApplicationContainer.obsidian.obsidian_service.provider]),
) -> SkillAcquisitionJobResponse:
    """Create a durable skill-acquisition job.

    Args:
        request: Skill-acquisition job request.
        service: Skill-acquisition application service.

    Returns:
        Created durable job response.
    """
    job = await service.request_job(
        prompt=request.prompt,
        agent_name=request.agent_name,
        project=request.project,
        task_summary=request.task_summary,
        provider_id=request.provider_id,
        librarian_profile_id=request.librarian_profile_id,
        search_snapshot=request.search_snapshot,
        acquisition_override_reason=request.acquisition_override_reason,
    )
    if job.status is SkillAcquisitionJobStatus.ACCEPTED:
        background_tasks.add_task(
            _run_skill_acquisition_background_job,
            database=database,
            runner_factory=runner_factory,
            obsidian_service_factory=obsidian_service_factory,
            job_id=job.id,
        )
    return skill_acquisition_job_response(job)


@router.get(
    "/skill-acquisition-jobs/{job_id}",
    response_model=SkillAcquisitionJobResponse,
    description="Return a durable skill-acquisition job status/result.",
    status_code=status.HTTP_200_OK,
    summary="Get skill acquisition job",
)
@router_exception_status(LIBRARIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def get_skill_acquisition_job(
    job_id: str,
    service: SkillAcquisitionService = Depends(
        Provide[ApplicationContainer.librarian.skill_acquisition_service]
    ),
) -> SkillAcquisitionJobResponse:
    """Return one durable skill-acquisition job.

    Args:
        job_id: Skill-acquisition job identifier.
        service: Skill-acquisition application service.

    Returns:
        Durable job response.
    """
    job = await service.get_job(job_id)
    return skill_acquisition_job_response(job)


@router.post(
    "/skill-acquisition-jobs/{job_id}/complete",
    response_model=SkillAcquisitionJobResponse,
    description="Persist an acquired skill artifact and attach a resume context.",
    status_code=status.HTTP_200_OK,
    summary="Complete skill acquisition job",
)
@router_exception_status(LIBRARIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def complete_skill_acquisition_job(
    job_id: str,
    request: SkillAcquisitionCompletionRequest,
    service: SkillAcquisitionService = Depends(
        Provide[ApplicationContainer.librarian.skill_acquisition_service]
    ),
    obsidian_service: ObsidianService = Depends(
        Provide[ApplicationContainer.obsidian.obsidian_service]
    ),
) -> SkillAcquisitionJobResponse:
    """Complete one durable skill-acquisition job with a structured artifact.

    Args:
        job_id: Skill-acquisition job identifier.
        request: Structured acquired skill artifact.
        service: Skill-acquisition application service.
        obsidian_service: Obsidian service used to save the draft skill artifact.

    Returns:
        Completed durable job response with skill/context handles.
    """
    job = await service.complete_with_skill_artifact(
        job_id=job_id,
        artifact=request.to_artifact(),
        artifact_publisher=ObsidianSkillArtifactPublisher(obsidian_service),
    )
    return skill_acquisition_job_response(job)
