"""Librarian runtime operations: recommend/classify/candidate generation."""

from __future__ import annotations

from app.container import ApplicationContainer
from app.librarian.application.hermes_collaboration_service import (
    HermesCollaborationService,
)
from app.librarian.application.knowledge_packet_compiler import KnowledgePacketCompiler
from app.librarian.application.librarian_ops_service import LibrarianOpsService
from app.librarian.application.skill_acquisition_runner import SkillAcquisitionRunner
from app.librarian.application.skill_acquisition_service import SkillAcquisitionService
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
from app.librarian.interface.schemas.librarian.librarian_ops_schemas import (
    ClassifyRequest,
    CreateCandidateRequest,
    RecommendRequest,
)
from app.librarian.interface.schemas.librarian.skill_acquisition_schemas import (
    SkillAcquisitionCompletionRequest,
    SkillAcquisitionJobRequest,
    SkillAcquisitionJobResponse,
    skill_acquisition_job_response,
)
from app.library.application.item_search_service import ItemSearchService
from app.library.domain.event_enum.item_enums import ItemType
from app.library.interface.schemas.item.item_schema import (
    ClassificationResponse,
    ItemResponse,
)
from app.library.interface.schemas.item.item_search_schema import ItemSearchResponse
from app.platform.security.operator_api_key import require_operator_api_key
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import LIBRARIAN_ROUTE_EXCEPTION_MAPPING
from app.shared.types.types_convert_utils import enum_value
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, BackgroundTasks, Depends, status

router = APIRouter(
    prefix="/librarians",
    tags=["librarian"],
    dependencies=[Depends(require_operator_api_key)],
)


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
    command = request.to_command(librarian_brief=brief.packet_markdown)
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
    description="Library API operation.",
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
    description="Library API operation.",
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
    runner: SkillAcquisitionRunner = Depends(
        Provide[ApplicationContainer.librarian.skill_acquisition_runner]
    ),
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
    )
    if job.status is SkillAcquisitionJobStatus.ACCEPTED:
        background_tasks.add_task(runner.run_job, job.id)
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
) -> SkillAcquisitionJobResponse:
    """Complete one durable skill-acquisition job with a structured artifact.

    Args:
        job_id: Skill-acquisition job identifier.
        request: Structured acquired skill artifact.
        service: Skill-acquisition application service.

    Returns:
        Completed durable job response with skill/context handles.
    """
    job = await service.complete_with_skill_artifact(
        job_id=job_id,
        artifact=request.to_artifact(),
    )
    return skill_acquisition_job_response(job)


@router.post(
    "/recommend",
    response_model=ItemSearchResponse,
    description="Recommend lightweight library candidates without full content.",
    status_code=status.HTTP_200_OK,
    summary="Recommend",
)
@router_exception_status(LIBRARIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def recommend(
    request: RecommendRequest,
    item_search_service: ItemSearchService = Depends(
        Provide[ApplicationContainer.library.item_search_service]
    ),
) -> ItemSearchResponse:
    """Recommend items by query with simple keyword search fallback.

    Args:
        request [RecommendRequest]: Value supplied to recommend.
        item_search_service [ItemSearchService]: Value supplied to recommend.

    Returns:
        ItemSearchResponse: Value produced by recommend.
    """
    payload = await item_search_service.search(
        query=request.query,
        item_type=enum_value(request.item_type, ItemType, "item_type"),
        limit=request.limit,
    )
    validation = ItemSearchResponse.model_validate(payload)
    return validation


@router.post(
    "/classify",
    response_model=ClassificationResponse,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Classify",
)
@router_exception_status(LIBRARIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def classify(
    request: ClassifyRequest,
    librarian_ops_service: LibrarianOpsService = Depends(
        Provide[ApplicationContainer.librarian.librarian_ops_service]
    ),
) -> ClassificationResponse:
    """Classify prompt into rough taxonomy categories.

    Args:
        request [ClassifyRequest]: Value supplied to classify.
        librarian_ops_service: Librarian operation application service.

    Returns:
        ClassificationResponse: Value produced by classify.
    """
    payload = librarian_ops_service.classify(request.text)
    validation = ClassificationResponse.model_validate(payload)
    return validation


@router.post(
    "/create-skill-candidate",
    response_model=ItemResponse,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Create skill candidate",
)
@router_exception_status(LIBRARIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def create_skill_candidate(
    request: CreateCandidateRequest,
    librarian_ops_service: LibrarianOpsService = Depends(
        Provide[ApplicationContainer.librarian.librarian_ops_service]
    ),
) -> ItemResponse:
    """Generate candidate payload and return draft candidate.

    Args:
        request [CreateCandidateRequest]: Value supplied to create_skill_candidate.
        librarian_ops_service: Librarian operation application service.

    Returns:
        ItemResponse: Value produced by create_skill_candidate.
    """
    payload = librarian_ops_service.generate_skill_candidate(
        provider_id=request.provider_id,
        prompt=request.prompt,
        category_id=request.category_id,
    )
    validation = ItemResponse.model_validate(payload)
    return validation
