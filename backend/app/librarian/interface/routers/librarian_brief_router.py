"""Routes for compiling librarian knowledge packet previews."""

from __future__ import annotations

from app.container import ApplicationContainer
from app.librarian.application.knowledge_packet_compiler import KnowledgePacketCompiler
from app.librarian.interface.schemas.librarian.librarian_brief_schemas import (
    BudgetPolicySchema,
    LibrarianBriefPreviewRequest,
    LibrarianBriefPreviewResponse,
    SourceRefSchema,
)
from app.platform.security.operator_api_key import require_operator_api_key
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import LIBRARIAN_ROUTE_EXCEPTION_MAPPING
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status

router = APIRouter(
    prefix="/librarians",
    tags=["librarian"],
    dependencies=[Depends(require_operator_api_key)],
)


@router.post(
    "/brief-preview",
    response_model=LibrarianBriefPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview librarian knowledge packet",
    description="Compile a budgeted compact/source-ref packet for librarian delegation.",
)
@router_exception_status(LIBRARIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def brief_preview(
    request: LibrarianBriefPreviewRequest,
    compiler: KnowledgePacketCompiler = Depends(
        Provide[ApplicationContainer.librarian.knowledge_packet_compiler]
    ),
) -> LibrarianBriefPreviewResponse:
    """Compile a librarian brief preview without delegating externally.

    Args:
        request: Prompt, budget, compact, and source-reference inputs.
        compiler: Knowledge packet compiler dependency.

    Returns:
        Compiled librarian brief preview response.
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
    payload = brief.to_payload()
    return LibrarianBriefPreviewResponse(
        prompt=payload["prompt"],
        project=payload["project"],
        packet_markdown=payload["packet_markdown"],
        source_refs=[
            SourceRefSchema(
                source_type=source_ref["source_type"],
                source_id=source_ref["source_id"],
                title=source_ref["title"],
                detail_path=source_ref["detail_path"],
                preview=source_ref["preview"],
            )
            for source_ref in payload["source_refs"]
        ],
        budget_policy=BudgetPolicySchema(**payload["budget_policy"]),
    )
